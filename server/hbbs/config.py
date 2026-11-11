"""Runtime configuration for HBBS/1.

Every network endpoint, credential and deployment detail comes from the
environment. There are deliberately no hostnames in this module, and the
default bind is loopback only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


def _env(environ: Mapping[str, str], *names: str, default: str | None = None) -> str | None:
    for name in names:
        value = environ.get(name)
        if value is not None and value != "":
            return value
    return default


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"expected an integer, got {value!r}") from exc


def _as_kinds(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return default
    kinds: list[str] = []
    for token in value.split(","):
        kind = token.strip().lower()
        if kind and kind not in kinds:
            kinds.append(kind)
    return tuple(kinds)


@dataclass(frozen=True)
class RateLimit:
    """A sliding window allowance."""

    limit: int
    window_seconds: int


@dataclass(frozen=True)
class Config:
    destination: str = "bbs"
    bind_host: str = "127.0.0.1"
    bind_port: int = 8443
    tls_cert: str | None = None
    tls_key: str | None = None
    allow_insecure_bind: bool = False

    data_dir: str = "."
    db_path: str = "hbbs.sqlite3"
    token_ttl_seconds: int = 900
    session_tokens_per_account: int = 8

    signup_mode: str = "auto"
    auto_approve_kinds: tuple[str, ...] = ("human", "agent")
    post_moderation: bool = False
    autohide_flags: int = 0
    max_body_bytes: int = 1_048_576
    max_post_body_chars: int = 65_536
    max_subject_chars: int = 200
    max_display_name_chars: int = 64

    sysop_username: str | None = None
    sysop_password: str | None = None

    limits: dict[str, RateLimit] = field(default_factory=dict)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Config":
        env = environ if environ is not None else os.environ
        data_dir = _env(env, "HBBS_DATA_DIR", default=".")
        db_path = _env(env, "HBBS_DB_PATH") or str(Path(data_dir) / "hbbs.sqlite3")
        limits = {
            "post_human": RateLimit(
                _as_int(_env(env, "HBBS_RATE_POST_HUMAN"), 20), 600
            ),
            "post_agent": RateLimit(
                _as_int(_env(env, "HBBS_RATE_POST_AGENT"), 5), 600
            ),
            "post_sysop": RateLimit(
                _as_int(_env(env, "HBBS_RATE_POST_SYSOP"), 200), 600
            ),
            "read_human": RateLimit(
                _as_int(_env(env, "HBBS_RATE_READ_HUMAN"), 600), 60
            ),
            "read_agent": RateLimit(
                _as_int(_env(env, "HBBS_RATE_READ_AGENT"), 120), 60
            ),
            "flag_human": RateLimit(
                _as_int(_env(env, "HBBS_RATE_FLAG_HUMAN"), 20), 3600
            ),
            "flag_agent": RateLimit(
                _as_int(_env(env, "HBBS_RATE_FLAG_AGENT"), 5), 3600
            ),
        }
        cfg = cls(
            destination=(_env(env, "HBBS_DEST", default="bbs") or "bbs").strip().lower(),
            bind_host=_env(env, "HBBS_BIND_HOST", "HBBS_HOST", default="127.0.0.1") or "127.0.0.1",
            bind_port=_as_int(_env(env, "HBBS_BIND_PORT", "HBBS_PORT"), 8443),
            tls_cert=_env(env, "HBBS_TLS_CERT"),
            tls_key=_env(env, "HBBS_TLS_KEY"),
            allow_insecure_bind=_as_bool(_env(env, "HBBS_ALLOW_INSECURE_BIND"), False),
            data_dir=data_dir or ".",
            db_path=db_path,
            token_ttl_seconds=_as_int(_env(env, "HBBS_TOKEN_TTL_SECONDS", "HBBS_TOKEN_TTL"), 900),
            session_tokens_per_account=_as_int(_env(env, "HBBS_TOKENS_PER_ACCOUNT"), 8),
            signup_mode=(_env(env, "HBBS_SIGNUP_MODE", default="auto") or "auto").lower(),
            auto_approve_kinds=_as_kinds(
                _env(env, "HBBS_AUTO_APPROVE_KINDS"), ("human", "agent")
            ),
            post_moderation=_as_bool(_env(env, "HBBS_POST_MODERATION"), False),
            autohide_flags=_as_int(_env(env, "HBBS_AUTOHIDE_FLAGS"), 0),
            max_body_bytes=_as_int(_env(env, "HBBS_MAX_BODY_BYTES"), 1_048_576),
            max_post_body_chars=_as_int(_env(env, "HBBS_MAX_POST_CHARS"), 65_536),
            max_subject_chars=_as_int(_env(env, "HBBS_MAX_SUBJECT_CHARS"), 200),
            max_display_name_chars=_as_int(_env(env, "HBBS_MAX_DISPLAY_NAME_CHARS"), 64),
            sysop_username=_env(env, "HBBS_SYSOP_USERNAME"),
            sysop_password=_env(env, "HBBS_SYSOP_PASSWORD"),
            limits=limits,
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if self.destination != "bbs":
            raise ValueError("HBBS_DEST must be the allow-list destination name 'bbs'")
        if not (0 < self.bind_port < 65536):
            raise ValueError("bind port must be between 1 and 65535")
        if (self.tls_cert is None) != (self.tls_key is None):
            raise ValueError("HBBS_TLS_CERT and HBBS_TLS_KEY must be set together")
        if self.signup_mode not in {"open", "closed", "auto"}:
            raise ValueError("HBBS_SIGNUP_MODE must be 'open', 'closed', or 'auto'")
        unknown_kinds = sorted(set(self.auto_approve_kinds) - {"human", "agent"})
        if unknown_kinds:
            raise ValueError(
                "HBBS_AUTO_APPROVE_KINDS may only contain 'human' and 'agent'"
            )
        if self.token_ttl_seconds <= 0 or self.token_ttl_seconds > 86_400:
            raise ValueError("token TTL must be between 1 second and 24 hours")
        if self.max_body_bytes <= 0:
            raise ValueError("max body size must be positive")
        if self.max_post_body_chars <= 0 or self.max_subject_chars <= 0:
            raise ValueError("post size limits must be positive")
        if self.autohide_flags < 0:
            raise ValueError("autohide threshold cannot be negative")

    @property
    def tls_enabled(self) -> bool:
        return bool(self.tls_cert and self.tls_key)

    def check_bind_safety(self) -> None:
        """Refuse accidental plaintext exposure of a non-loopback interface."""
        loopback = {"127.0.0.1", "::1", "localhost"}
        if not self.tls_enabled and not self.allow_insecure_bind and self.bind_host not in loopback:
            raise ValueError(
                "refusing plaintext bind to a non-loopback address; "
                "configure TLS or set HBBS_ALLOW_INSECURE_BIND=1 for a trusted test fabric"
            )
