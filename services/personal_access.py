"""Password hashing, bounded login attempts and expiring single-owner sessions."""

import argparse
import base64
import binascii
import getpass
import hashlib
import hmac
import math
import secrets
import threading
import time
import warnings
from collections import deque
from dataclasses import dataclass

ITERATIONS = 600_000
IDLE_SECONDS = 30 * 60
MAX_SESSION_SECONDS = 12 * 60 * 60


def _decode_hash(encoded):
    try:
        algorithm, rounds, salt, digest = encoded.split("$")
        rounds = int(rounds)
        salt = base64.b64decode(salt, altchars=b"-_", validate=True)
        digest = base64.b64decode(digest, altchars=b"-_", validate=True)
        if algorithm != "pbkdf2_sha256" or not ITERATIONS <= rounds <= 2_000_000:
            return None
        if not 16 <= len(salt) <= 64 or len(digest) != 32:
            return None
        return rounds, salt, digest
    except (AttributeError, TypeError, ValueError, binascii.Error):
        return None


def configured_password(encoded):
    return _decode_hash(encoded) is not None


def hash_password(password):
    """Generate a salted verifier; the original password is never returned or saved."""
    if not isinstance(password, str) or not 12 <= len(password) <= 1024:
        raise ValueError("Choose a password between 12 and 1024 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return "$".join(
        (
            "pbkdf2_sha256",
            str(ITERATIONS),
            base64.urlsafe_b64encode(salt).decode(),
            base64.urlsafe_b64encode(digest).decode(),
        )
    )


def verify_password(password, encoded):
    parameters = _decode_hash(encoded)
    if parameters is None or not isinstance(password, str) or len(password) > 1024:
        return False
    rounds, salt, expected = parameters
    try:
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    except UnicodeEncodeError:
        return False
    return hmac.compare_digest(actual, expected)


def password_fingerprint(encoded):
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OwnerSession:
    fingerprint: str
    started_at: float
    active_at: float


def valid_session(session, encoded, now):
    """Reject forged flags, expired sessions and sessions using a rotated verifier."""
    return (
        isinstance(session, OwnerSession)
        and configured_password(encoded)
        and hmac.compare_digest(session.fingerprint, password_fingerprint(encoded))
        and 0 <= now - session.active_at < IDLE_SECONDS
        and 0 <= now - session.started_at < MAX_SESSION_SECONDS
    )


class LoginLimiter:
    """Reserve attempts before hashing, across tabs and concurrent browser sessions."""

    def __init__(self, *, clock=time.monotonic):
        self.clock = clock
        self.window = 60
        self.peers = {}
        self.attempts = deque()
        self.salt = secrets.token_bytes(32)
        self.lock = threading.Lock()

    def reserve(self, peer):
        """Return seconds to wait, or reserve one of five peer / thirty global attempts."""
        peer = peer if isinstance(peer, str) and peer else "unknown"
        identity = hmac.new(self.salt, peer.encode(), "sha256").digest()
        with self.lock:
            now = self.clock()
            while self.attempts and self.attempts[0] <= now - self.window:
                self.attempts.popleft()
            self.peers = {
                key: deque(value for value in values if value > now - self.window)
                for key, values in self.peers.items()
                if values and values[-1] > now - self.window
            }
            if len(self.attempts) >= 30:
                return max(1, math.ceil(self.window - (now - self.attempts[0])))
            attempts = self.peers.setdefault(identity, deque())
            if len(attempts) >= 5:
                return max(1, math.ceil(self.window - (now - attempts[0])))
            attempts.append(now)
            self.attempts.append(now)
            return 0


def main():
    argparse.ArgumentParser(
        description="Generate a personal workspace password verifier."
    ).parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            password = getpass.getpass("Personal workspace password (at least 12 characters): ")
            confirmation = getpass.getpass("Repeat password: ")
        except getpass.GetPassWarning:
            raise SystemExit(
                "Run this command in an interactive terminal with hidden input."
            ) from None
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    try:
        encoded = hash_password(password)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print(f'PERSONAL_PASSWORD_HASH = "{encoded}"')


if __name__ == "__main__":
    main()
