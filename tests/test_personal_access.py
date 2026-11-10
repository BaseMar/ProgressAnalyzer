"""Exercise the hosted owner gate, cache isolation and session transitions."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import text
from streamlit.testing.v1 import AppTest

from data_loader import load_data
from db.public_demo import create_demo_database
from services.personal_access import (
    IDLE_SECONDS,
    ITERATIONS,
    MAX_SESSION_SECONDS,
    LoginLimiter,
    OwnerSession,
    configured_password,
    hash_password,
    password_fingerprint,
    valid_session,
    verify_password,
)
from services.personal_access import main as password_command
from ui.access_view import AUTH_KEY, PASSWORD_KEY

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "Synthetic owner password 123!"


@pytest.fixture(scope="module")
def verifier():
    return hash_password(PASSWORD)


@pytest.fixture
def owner_database(monkeypatch, verifier):
    database = create_demo_database()
    with database.engine.begin() as connection:
        connection.execute(text("UPDATE training_plan_versions SET name='Private owner plan'"))
    monkeypatch.setenv("PERSONAL_PASSWORD_HASH", verifier)
    load_data.clear()
    with (
        patch("db.connection._get_personal_engine", return_value=database.engine) as reads,
        patch("ui.access_view.login_limiter", return_value=LoginLimiter()),
    ):
        yield database.engine, reads
    load_data.clear()
    database.engine.dispose()


def hosted_app():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    assert not app.exception and not app.error
    return app


def unlock(app, password=PASSWORD):
    app.sidebar.radio(key="workspace_mode").set_value("Personal").run()
    app.text_input(key=PASSWORD_KEY).set_value(password)
    app.button(key="owner_login_submit").click().run()
    return app


def test_password_verifiers_are_salted_and_accept_unicode(verifier):
    assert verify_password(PASSWORD, verifier)
    assert not verify_password(PASSWORD + "wrong", verifier)
    assert hash_password(PASSWORD) != verifier
    unicode_password = "Długi trening siłowy 123!"
    assert verify_password(unicode_password, hash_password(unicode_password))


@pytest.mark.parametrize("value", [None, "", "plaintext", "pbkdf2_sha256$999999999$x$x"])
def test_missing_or_malformed_verifier_fails_closed(value):
    assert not configured_password(value)
    assert not verify_password(PASSWORD, value)


def test_weak_passwords_and_extreme_input_are_rejected(verifier):
    with pytest.raises(ValueError, match="12"):
        hash_password("short")
    assert not verify_password("x" * 1025, verifier)
    assert not verify_password("\ud800", verifier)
    assert str(ITERATIONS) in verifier


def test_limiter_reserves_concurrent_attempts_and_expires_them():
    now = [100.0]
    limiter = LoginLimiter(clock=lambda: now[0])
    assert [limiter.reserve("same peer") for _ in range(5)] == [0] * 5
    assert limiter.reserve("same peer") == 60
    assert limiter.reserve("another peer") == 0
    now[0] += 60
    assert limiter.reserve("same peer") == 0


def test_global_limiter_bounds_attempts_with_different_peers():
    limiter = LoginLimiter(clock=lambda: 10.0)
    assert [limiter.reserve(str(peer)) for peer in range(30)] == [0] * 30
    assert limiter.reserve("new peer") == 60


def test_expiry_rotation_and_forged_session_flags(verifier):
    session = OwnerSession(password_fingerprint(verifier), 100.0, 100.0)
    assert valid_session(session, verifier, 101)
    assert not valid_session(True, verifier, 101)
    assert not valid_session(session, verifier, 100 + IDLE_SECONDS)
    assert not valid_session(session, hash_password(PASSWORD), 101)
    assert not valid_session(
        replace(session, active_at=100 + MAX_SESSION_SECONDS), verifier, 100 + MAX_SESSION_SECONDS
    )


def test_demo_and_failed_login_never_read_private_database(owner_database):
    _, reads = owner_database
    app = hosted_app()
    reads.assert_not_called()
    assert app.sidebar.button(key="reset_public_demo")
    app.sidebar.radio(key="workspace_mode").set_value("Personal").run()
    reads.assert_not_called()
    assert not any(button.key == "nav_Overview" for button in app.sidebar.button)
    unlock(app, "Incorrect synthetic password")
    reads.assert_not_called()
    assert not app.exception
    assert app.error[0].value == "Incorrect password."
    assert app.text_input(key=PASSWORD_KEY).value == ""


def test_owner_can_open_every_route_and_logout_clears_private_drafts(owner_database):
    _, reads = owner_database
    app = unlock(hosted_app())
    assert not app.exception and not app.error
    assert reads.called
    assert PASSWORD_KEY not in app.session_state
    assert "Private owner plan" in app.selectbox[0].options
    for page in ("Analysis", "Plan", "History", "Overview"):
        app.sidebar.button(key="nav_" + page).click().run()
        assert not app.exception and not app.error
    app.session_state["private_editor_draft"] = "Only for the owner"
    app.sidebar.button(key="owner_logout").click().run()
    assert not app.exception and not app.error
    assert AUTH_KEY not in app.session_state
    assert "private_editor_draft" not in app.session_state
    assert app.sidebar.radio(key="workspace_mode").value == "Demo"
    assert "Private owner plan" not in app.selectbox[0].options
    app.sidebar.radio(key="workspace_mode").set_value("Personal").run()
    assert app.text_input(key=PASSWORD_KEY)


def test_switching_modes_requires_reauthentication(owner_database):
    app = unlock(hosted_app())
    app.session_state["private_editor_draft"] = "Private draft"
    app.sidebar.radio(key="workspace_mode").set_value("Demo").run()
    assert "private_editor_draft" not in app.session_state
    app.sidebar.radio(key="workspace_mode").set_value("Personal").run()
    assert AUTH_KEY not in app.session_state
    assert app.text_input(key=PASSWORD_KEY)


def test_expired_session_removes_private_state_before_database_read(owner_database, verifier):
    _, reads = owner_database
    app = unlock(hosted_app())
    reads.reset_mock()
    session = app.session_state[AUTH_KEY]
    app.session_state[AUTH_KEY] = replace(session, active_at=session.active_at - IDLE_SECONDS)
    app.session_state["private_editor_draft"] = "Expired draft"
    app.run()
    reads.assert_not_called()
    assert not app.exception
    assert AUTH_KEY not in app.session_state
    assert "private_editor_draft" not in app.session_state
    assert app.text_input(key=PASSWORD_KEY)


def test_unconfigured_personal_mode_keeps_demo_available(monkeypatch):
    monkeypatch.setenv("PERSONAL_PASSWORD_HASH", "invalid-not-a-password-hash")
    with patch("db.connection._get_personal_engine", side_effect=AssertionError("Private read")):
        app = hosted_app()
        app.sidebar.radio(key="workspace_mode").set_value("Personal").run()
        assert not app.exception
        assert app.button(key="owner_login_submit").disabled
        app.sidebar.radio(key="workspace_mode").set_value("Demo").run()
        assert not app.exception and not app.error


def test_one_authenticated_browser_does_not_unlock_another(owner_database):
    owner = unlock(hosted_app())
    visitor = hosted_app()
    visitor.sidebar.radio(key="workspace_mode").set_value("Personal").run()
    assert AUTH_KEY in owner.session_state
    assert AUTH_KEY not in visitor.session_state
    assert visitor.text_input(key=PASSWORD_KEY)


def test_password_rotation_revokes_the_open_workspace(owner_database, monkeypatch):
    _, reads = owner_database
    app = unlock(hosted_app())
    reads.reset_mock()
    monkeypatch.setenv("PERSONAL_PASSWORD_HASH", hash_password("A different owner password!"))
    app.run()
    reads.assert_not_called()
    assert not app.exception
    assert AUTH_KEY not in app.session_state
    assert app.text_input(key=PASSWORD_KEY)


def test_login_throttle_blocks_correct_password_until_retry(owner_database):
    _, reads = owner_database
    app = hosted_app()
    for _ in range(5):
        unlock(app, "Wrong synthetic password")
        assert not app.exception
    unlock(app)
    reads.assert_not_called()
    assert "Too many attempts" in app.error[0].value
    assert app.text_input(key=PASSWORD_KEY).value == ""


def test_verifier_command_prints_only_the_config_line(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["personal_access"])
    monkeypatch.setattr("getpass.getpass", lambda _: PASSWORD)
    password_command()
    output = capsys.readouterr().out
    assert output.startswith('PERSONAL_PASSWORD_HASH = "pbkdf2_sha256$')
    assert PASSWORD not in output
    assert verify_password(PASSWORD, output.split('"')[1])
