"""Select the public sandbox or unlock the owner's database before any private read."""

import os
import time
from dataclasses import replace

import streamlit as st
from dotenv import find_dotenv, load_dotenv

from services.personal_access import (
    LoginLimiter,
    OwnerSession,
    configured_password,
    password_fingerprint,
    valid_session,
    verify_password,
)
from ui.utils.ui_helpers import page_title

AUTH_KEY = "_owner_access_session"
MODE_KEY = "workspace_mode"
PASSWORD_KEY = "owner_password_input"


def password_setting():
    load_dotenv(find_dotenv(usecwd=True) or None)
    value = os.getenv("PERSONAL_PASSWORD_HASH")
    if value:
        return value
    try:
        return st.secrets.get("PERSONAL_PASSWORD_HASH")
    except Exception:
        return None


@st.cache_resource
def login_limiter():
    return LoginLimiter()


def _clear_workspace(mode, *, session=None, notice=None):
    """Discard editor drafts, selected records, credentials and cached UI state."""
    st.session_state.clear()
    st.session_state[MODE_KEY] = mode
    if session is not None:
        st.session_state[AUTH_KEY] = session
    if notice is not None:
        st.session_state["owner_access_notice"] = notice


def _switch_workspace():
    mode = st.session_state.get(MODE_KEY, "Demo")
    _clear_workspace(mode if mode in ("Demo", "Personal") else "Demo")


def _logout():
    from data_loader import load_data

    load_data.clear("personal")
    _clear_workspace("Demo")


def _authenticate():
    password = st.session_state.get(PASSWORD_KEY, "")
    st.session_state[PASSWORD_KEY] = ""
    encoded = password_setting()
    if not configured_password(encoded):
        st.session_state["owner_access_error"] = "Personal access is not configured."
        return
    retry = login_limiter().reserve(st.context.ip_address)
    if retry:
        st.session_state["owner_access_error"] = f"Too many attempts. Try again in {retry} seconds."
        return
    if not verify_password(password, encoded):
        st.session_state["owner_access_error"] = "Incorrect password."
        return
    now = time.monotonic()
    session = OwnerSession(password_fingerprint(encoded), now, now)
    _clear_workspace("Personal", session=session)


def select_workspace():
    """Return True only for an authenticated personal workspace; stop at its gate otherwise."""
    st.sidebar.radio("Workspace", ["Demo", "Personal"], key=MODE_KEY, on_change=_switch_workspace)
    if st.session_state[MODE_KEY] != "Personal":
        # A client can change the widget without preserving an old owner session.
        st.session_state.pop(AUTH_KEY, None)
        return False
    encoded = password_setting()
    session = st.session_state.get(AUTH_KEY)
    now = time.monotonic()
    if valid_session(session, encoded, now):
        st.session_state[AUTH_KEY] = replace(session, active_at=now)
        st.sidebar.caption("Personal workspace · Your saved training data")
        st.sidebar.button("Log out", key="owner_logout", on_click=_logout)
        return True
    if session is not None:
        _clear_workspace("Personal", notice="Your session expired. Please sign in again.")
        st.rerun()
    page_title("Personal", "Your personal workspace")
    st.caption("Unlock your saved training plan and history.")
    if "owner_access_notice" in st.session_state:
        st.info(st.session_state.pop("owner_access_notice"))
    ready = configured_password(encoded)
    if not ready:
        st.info(
            "Personal access has not been enabled by the owner. The demo is available without signing in."
        )
    if "owner_access_error" in st.session_state:
        st.error(st.session_state.pop("owner_access_error"))
    with st.form("owner_login_form"):
        st.text_input("Password", type="password", key=PASSWORD_KEY, disabled=not ready)
        st.form_submit_button(
            "Unlock personal workspace",
            key="owner_login_submit",
            on_click=_authenticate,
            disabled=not ready,
        )
    st.stop()
