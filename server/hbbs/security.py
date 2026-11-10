"""Password hashing and opaque AUTH tokens.

Passwords use scrypt from the standard library, so the server has no runtime
dependencies. Tokens are random bearer values; only their SHA-256 digest is
stored, which makes a leaked database snapshot less useful.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Final

_SCRYPT_N: Final = 2**14
_SCRYPT_R: Final = 8
_SCRYPT_P: Final = 1
_SCRYPT_DKLEN: Final = 32
_SALT_BYTES: Final = 16

_PASSWORD_SCHEME: Final = "scrypt"

USERNAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_.-]{0,30}[a-z0-9])?$")
BOARD_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if not isinstance(password, str):
        raise TypeError("password must be text")
    salt = salt or secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return f"{_PASSWORD_SCHEME}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = encoded.split("$", 2)
        if scheme != _PASSWORD_SCHEME:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (AttributeError, ValueError):
        return False
    if not password or not expected:
        return False
    candidate = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=len(expected),
    )
    return hmac.compare_digest(candidate, expected)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_username(username: str) -> str:
    return username.strip().lower()


def valid_username(username: str) -> bool:
    return bool(USERNAME_RE.fullmatch(username))


def contains_control(value: str) -> bool:
    return any(ord(ch) < 32 and ch not in "\t\n\r" for ch in value)
