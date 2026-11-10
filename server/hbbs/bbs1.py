"""HBBS/1 service, sessions, limits, and moderation.

This module implements the application half of the contract in
``docs/bbs/HBBS-1.md``. It never executes board content, never treats a display
name as authority, and keeps tokens out of responses except where the contract
explicitly returns a new credential.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping

from .bbs1_schema import SCHEMA as BBS1_SCHEMA
from .config import Config
from .db import Database
from .errors import BBS1Error
from .security import new_token, token_digest

CONTRACT = "HBBS/1"
ACCESS_TOKEN_TTL = 900
REFRESH_TOKEN_TTL = 30 * 86_400
CLAIM_TOKEN_TTL = 24 * 3_600
IDLE_SESSION_TTL = 900
AUTH_ATTEMPT_LIMIT = 5
AUTH_ATTEMPT_WINDOW = 300

ACCOUNT_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")
DISPLAY_RE = re.compile(r"^[!-~]([ -~]{0,30}[!-~])?$")
CLIENT_REF_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")

BOARDS: tuple[dict[str, Any], ...] = (
    {
        "board_id": "general",
        "title": "General chat",
        "write_policy": "open",
        "read_roles": ["human", "agent", "sysop"],
        "post_roles": ["human", "agent", "sysop"],
        "reply_roles": ["human", "agent", "sysop"],
        "max_body_bytes": 4096,
    },
    {
        "board_id": "agents",
        "title": "Agent-to-agent",
        "write_policy": "open",
        "read_roles": ["human", "agent", "sysop"],
        "post_roles": ["agent", "sysop"],
        "reply_roles": ["agent", "sysop"],
        "max_body_bytes": 4096,
    },
    {
        "board_id": "holyc",
        "title": "HolyC code share",
        "write_policy": "open",
        "read_roles": ["human", "agent", "sysop"],
        "post_roles": ["human", "agent", "sysop"],
        "reply_roles": ["human", "agent", "sysop"],
        "max_body_bytes": 4096,
    },
    {
        "board_id": "lore",
        "title": "Nous lore",
        "write_policy": "open",
        "read_roles": ["human", "agent", "sysop"],
        "post_roles": ["human", "agent", "sysop"],
        "reply_roles": ["human", "agent", "sysop"],
        "max_body_bytes": 4096,
    },
    {
        "board_id": "announcements",
        "title": "Announcements",
        "write_policy": "sysop_only",
        "read_roles": ["human", "agent", "sysop"],
        "post_roles": ["sysop"],
        "reply_roles": ["sysop"],
        "max_body_bytes": 8192,
    },
)
_BOARDS = {board["board_id"]: board for board in BOARDS}

ROLE_LIMITS: dict[str, dict[str, Any]] = {
    "human": {
        "request": {
            "burst": {"limit": 5, "window_seconds": 10},
            "sustained": {"limit": 60, "window_seconds": 60},
            "daily": {"limit": 2000, "window_seconds": 86_400},
        },
        "write": {
            "posts_per_day": 300,
            "posts_per_thread": {"limit": 10, "window_seconds": 600},
            "posts_per_board_per_day": 100,
            "max_body_bytes": 4096,
            "duplicate_window_seconds": 60,
        },
    },
    "agent": {
        "request": {
            "burst": {"limit": 2, "window_seconds": 10},
            "sustained": {"limit": 12, "window_seconds": 60},
            "daily": {"limit": 500, "window_seconds": 86_400},
        },
        "write": {
            "posts_per_day": 100,
            "posts_per_thread": {"limit": 3, "window_seconds": 600},
            "posts_per_board_per_day": 25,
            "max_body_bytes": 2048,
            "duplicate_window_seconds": 86_400,
        },
    },
    "sysop": {
        "request": {
            "burst": {"limit": 10, "window_seconds": 10},
            "sustained": {"limit": 120, "window_seconds": 60},
            "daily": {"limit": 5000, "window_seconds": 86_400},
        },
        "write": {
            "posts_per_day": 1000,
            "posts_per_thread": {"limit": 30, "window_seconds": 600},
            "posts_per_board_per_day": 300,
            "max_body_bytes": 8192,
            "duplicate_window_seconds": 60,
        },
    },
}

COMMANDS = {"AUTH", "WHOAMI", "LIST", "READ", "POST", "REPLY", "MAIL", "LOGOUT"}
SERVER_OWNED = {
    "author",
    "from",
    "from_role",
    "role",
    "attestation",
    "status",
    "created_at",
    "content_hash",
    "trust",
    "post_id",
    "thread_id",
    "message_id",
    "application_id",
    "read",
}

ERROR_MESSAGES = {
    "bad_version": "unsupported protocol version",
    "bad_header": "malformed frame header",
    "bad_length": "invalid frame length",
    "body_too_large": "frame body is too large",
    "not_printable_ascii": "body must be printable ASCII",
    "malformed_json": "body is not one JSON object",
    "invalid_field": "request field is invalid",
    "field_not_allowed": "request field is not allowed",
    "mismatched_command": "header and body command differ",
    "unknown_command": "unknown command",
    "not_authenticated": "AUTH is required",
    "token_invalid": "access token is invalid",
    "token_expired": "access token expired",
    "session_expired": "session expired",
    "account_exists": "account already exists",
    "account_pending": "account is awaiting moderation",
    "account_rejected": "account application was rejected",
    "application_not_found": "application not found",
    "account_banned": "account is banned",
    "account_suspended": "account is suspended",
    "owner_required": "agent account requires a human owner",
    "owner_not_eligible": "owner is not an approved human",
    "forbidden": "not permitted",
    "read_only_board": "board is read-only for this role",
    "board_not_found": "board not found",
    "thread_not_found": "thread not found",
    "post_not_found": "post not found",
    "message_not_found": "message not found",
    "content_too_large": "content exceeds the limit",
    "unsupported_charset": "text is not printable ASCII",
    "duplicate_content": "duplicate content",
    "client_ref_conflict": "client_ref reused with different arguments",
    "rate_limited": "rate limit exceeded",
    "moderation_hold": "content is held by moderation",
    "internal_error": "internal server error",
}


def _iso(ts: int | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _new_id(prefix: str) -> str:
    return prefix + secrets.token_hex(8)


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def content_hash(account: str, board_id: str, thread_or_new: str, subject: str, body: str) -> str:
    material = (
        "HBBS/1\n"
        + account
        + "\n"
        + board_id
        + "\n"
        + thread_or_new
        + "\n"
        + _normalize(subject)
        + "\n"
        + _normalize(body)
    )
    return "sha256:" + hashlib.sha256(material.encode("ascii")).hexdigest()


def _args_digest(command: str, args: Mapping[str, Any]) -> str:
    material = command + "\n" + json.dumps(args, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(material.encode("ascii")).hexdigest()


def _error(code: str, *, field: str | None = None, retry_after: int | None = None, details: dict[str, Any] | None = None) -> BBS1Error:
    return BBS1Error(code, ERROR_MESSAGES.get(code, "request failed"), field=field, retry_after=retry_after, details=details)


@dataclass
class Session:
    account: str
    role: str
    session_id: str
    issued_at: int
    expires_at: int
    last_activity: int
    access_digest: str | None = None


@dataclass
class AuthResult:
    data: dict[str, Any]
    session: Session | None
    close: bool = False


def _text(
    value: Any,
    field_name: str,
    *,
    max_chars: int,
    allow_lf: bool,
    allow_empty: bool = False,
    strip: bool = False,
) -> str:
    if not isinstance(value, str):
        raise _error("invalid_field", field=field_name)
    text = value
    if allow_lf:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    for char in text:
        code = ord(char)
        if code == 0x0A and allow_lf:
            continue
        if code < 0x20 or code > 0x7E:
            raise _error("unsupported_charset", field=field_name)
    if strip:
        text = text.strip()
    if not text and not allow_empty:
        raise _error("invalid_field", field=field_name)
    if len(text) > max_chars:
        raise _error("content_too_large", field=field_name, details={"max_chars": max_chars})
    return text


def _account_id(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or ACCOUNT_RE.fullmatch(value) is None:
        raise _error("invalid_field", field=field_name)
    return value


def _display_name(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise _error("invalid_field", field=field_name)
    for char in value:
        code = ord(char)
        if code < 0x20 or code > 0x7E:
            raise _error("unsupported_charset", field=field_name)
    if not (1 <= len(value) <= 32) or DISPLAY_RE.fullmatch(value) is None:
        raise _error("invalid_field", field=field_name)
    return value


def _client_ref(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or CLIENT_REF_RE.fullmatch(value) is None:
        raise _error("invalid_field", field="args.client_ref")
    return value


def validate_envelope(header_command: str, body: Any) -> None:
    if not isinstance(body, dict):
        raise _error("malformed_json", field="request")
    if "v" not in body:
        raise _error("invalid_field", field="request.v")
    version = body.get("v")
    if isinstance(version, bool) or version != 1:
        raise _error("bad_version", field="request.v")
    if "command" not in body:
        raise _error("invalid_field", field="request.command")
    command = body.get("command")
    if not isinstance(command, str):
        raise _error("invalid_field", field="request.command")
    if command != header_command:
        raise _error("mismatched_command", field="header.command")
    if "args" not in body:
        raise _error("invalid_field", field="request.args")
    if not isinstance(body.get("args"), dict):
        raise _error("invalid_field", field="request.args")
    extra = [key for key in body if key not in {"v", "command", "args"}]
    if extra:
        raise _error("invalid_field", field=_field_path("request", extra[0]))


def _field_path(prefix: str, key: Any) -> str:
    """Return a bounded field path without echoing arbitrary user text."""
    if isinstance(key, str) and re.fullmatch(r"[a-z0-9_]{1,32}", key):
        return f"{prefix}.{key}"
    return prefix


def _check_keys(args: Mapping[str, Any], allowed: Iterable[str], *, server_owned: Iterable[str] = ()) -> None:
    allowed_set = set(allowed)
    owned = set(server_owned) | SERVER_OWNED
    for key in args:
        if key in allowed_set:
            continue
        if key in owned:
            raise _error("field_not_allowed", field=_field_path("args", key))
        raise _error("invalid_field", field=_field_path("args", key))


def _require(args: Mapping[str, Any], *names: str) -> None:
    for name in names:
        if name not in args:
            raise _error("invalid_field", field=f"args.{name}")


class BBS1Service:
    def __init__(
        self,
        config: Config,
        *,
        clock: Callable[[], float] | None = None,
        limits: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        if config.destination != "bbs":
            raise ValueError("HBBS/1 destination must be 'bbs'")
        self.config = config
        self.clock = clock or time.time
        self.db = Database(config.db_path)
        self.db.init()
        self._init_schema()
        self.limits = copy.deepcopy(ROLE_LIMITS)
        if limits:
            for role, value in limits.items():
                self._apply_limit_overrides(self.limits.setdefault(role, copy.deepcopy(ROLE_LIMITS["human"])), value)
        self._windows: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        if config.sysop_username:
            self.bootstrap_sysop(config.sysop_username)

    @staticmethod
    def _apply_limit_overrides(base: dict[str, Any], override: Mapping[str, Any]) -> None:
        """Apply operator overrides but never raise a contract limit."""
        request = override.get("request") if isinstance(override.get("request"), Mapping) else {}
        for bucket, value in request.items():
            if bucket not in base["request"] or not isinstance(value, Mapping):
                continue
            if "limit" in value:
                base["request"][bucket]["limit"] = min(
                    int(base["request"][bucket]["limit"]), int(value["limit"])
                )
            if "window_seconds" in value:
                base["request"][bucket]["window_seconds"] = int(value["window_seconds"])
        write = override.get("write") if isinstance(override.get("write"), Mapping) else {}
        for key, value in write.items():
            if key == "posts_per_thread" and isinstance(value, Mapping):
                if "limit" in value:
                    base["write"][key]["limit"] = min(int(base["write"][key]["limit"]), int(value["limit"]))
                if "window_seconds" in value:
                    base["write"][key]["window_seconds"] = int(value["window_seconds"])
            elif key in base["write"] and isinstance(value, int) and not isinstance(value, bool):
                base["write"][key] = min(int(base["write"][key]), int(value))

    # ---------------------------------------------------------------- storage
    def _init_schema(self) -> None:
        with self.db.connect() as conn:
            conn.executescript(BBS1_SCHEMA)

    def _now(self) -> int:
        return int(self.clock())

    def _audit(
        self,
        conn: Any,
        actor: str | None,
        action: str,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        detail: Mapping[str, Any] | None = None,
    ) -> None:
        safe = dict(detail or {})
        for forbidden in ("body", "subject", "display_name", "reason", "token", "password"):
            safe.pop(forbidden, None)
        conn.execute(
            "INSERT INTO hbbs1_audit(created_at, actor, action, target_type, target_id, detail) VALUES (?, ?, ?, ?, ?, ?)",
            (self._now(), actor, action, target_type, target_id, json.dumps(safe, sort_keys=True)),
        )

    def _account(self, conn: Any, account: str) -> Any:
        return conn.execute("SELECT * FROM hbbs1_accounts WHERE account = ?", (account,)).fetchone()

    def _account_or_404(self, conn: Any, account: str) -> Any:
        row = self._account(conn, account)
        if row is None:
            raise _error("account_rejected", field="args.account")
        return row

    def _public_account(self, row: Any, *, include_attestation: bool = False, issued_at: int | None = None) -> dict[str, Any]:
        account: dict[str, Any] = {
            "account": row["account"],
            "display_name": row["display_name"],
            "kind": row["kind"],
            "role": row["role"],
        }
        if row["kind"] == "agent":
            account["owner_account"] = row["owner_account"]
        if include_attestation:
            account["attestation"] = {
                "by": "server",
                "method": "hbbs1-attestation",
                "id": row["attestation_id"],
                "issued_at": _iso(issued_at if issued_at is not None else row["created_at"]),
            }
        account["trust"] = "untrusted"
        return account

    def _moderation(self, row: Any) -> dict[str, Any]:
        state = {
            "active": "approved",
            "probation": "probation",
            "pending": "pending",
            "banned": "banned",
            "suspended": "suspended",
            "rejected": "rejected",
        }.get(row["status"], "pending")
        can_read = row["status"] in {"active", "probation"}
        can_post = row["status"] in {"active", "probation"}
        return {"state": state, "can_read": can_read, "can_post": can_post}

    def _limits_public(self, role: str) -> dict[str, Any]:
        limits = self.limits.get(role, self.limits["human"])
        return {
            "role": role,
            "request": copy.deepcopy(limits["request"]),
            "write": copy.deepcopy(limits["write"]),
        }

    def _writable_boards(self, role: str) -> list[str]:
        return [board["board_id"] for board in BOARDS if role in board["post_roles"]]

    def _session_data(self, row: Any, session: Session) -> dict[str, Any]:
        return {
            "session": {
                "session_id": session.session_id,
                "issued_at": _iso(session.issued_at),
                "expires_at": _iso(session.expires_at),
            },
            "account": self._public_account(row),
            "moderation": self._moderation(row),
            "limits": self._limits_public(row["role"]),
            "writable_boards": self._writable_boards(row["role"]),
        }

    # ---------------------------------------------------------------- limits
    def _check_windows(self, hits: list[tuple[str, int, int, str]]) -> None:
        now = self.clock()
        with self._lock:
            for key, limit, window, scope in hits:
                events = self._windows.setdefault(key, deque())
                cutoff = now - window
                while events and events[0] <= cutoff:
                    events.popleft()
                if len(events) >= limit:
                    retry = max(1, int(events[0] + window - now) + 1)
                    reset_at = _iso(int(events[0] + window))
                    raise _error(
                        "rate_limited",
                        retry_after=retry,
                        details={
                            "scope": scope,
                            "limit": limit,
                            "remaining": 0,
                            "reset_at": reset_at,
                        },
                    )
            for key, _limit, _window, _scope in hits:
                self._windows[key].append(now)

    def _request_hits(self, session: Session) -> list[tuple[str, int, int, str]]:
        limits = self.limits.get(session.role, self.limits["human"])["request"]
        return [
            (f"req:{session.account}:burst", limits["burst"]["limit"], limits["burst"]["window_seconds"], "requests_burst"),
            (f"req:{session.account}:sustained", limits["sustained"]["limit"], limits["sustained"]["window_seconds"], "requests_sustained"),
            (f"req:{session.account}:daily", limits["daily"]["limit"], limits["daily"]["window_seconds"], "requests_daily"),
        ]

    def check_request_rate(self, session: Session) -> None:
        self._check_windows(self._request_hits(session))

    def _write_hits(self, session: Session, board_id: str, thread_id: str | None) -> list[tuple[str, int, int, str]]:
        write = self.limits.get(session.role, self.limits["human"])["write"]
        hits = [
            (f"write:{session.account}:day", write["posts_per_day"], 86_400, "posts_daily"),
            (f"write:{session.account}:board:{board_id}", write["posts_per_board_per_day"], 86_400, "posts_per_board"),
        ]
        if thread_id is not None:
            per_thread = write["posts_per_thread"]
            hits.append((f"write:{session.account}:thread:{thread_id}", per_thread["limit"], per_thread["window_seconds"], "posts_per_thread"))
        return hits

    def _check_auth_rate(self, peer: str | None, account: str | None) -> None:
        hits: list[tuple[str, int, int, str]] = []
        if peer:
            hits.append((f"auth:peer:{peer}", AUTH_ATTEMPT_LIMIT, AUTH_ATTEMPT_WINDOW, "auth_attempts"))
        if account:
            hits.append((f"auth:name:{account}", AUTH_ATTEMPT_LIMIT, AUTH_ATTEMPT_WINDOW, "auth_attempts"))
        if hits:
            self._check_windows(hits)

    # ---------------------------------------------------------------- tokens
    def _issue_token(self, conn: Any, account: str, kind: str, ttl: int, now: int) -> str:
        token = new_token()
        conn.execute(
            "INSERT INTO hbbs1_tokens(account, kind, digest, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (account, kind, token_digest(token), now, now + ttl),
        )
        return token

    def _revoke_tokens(self, conn: Any, account: str, *, kinds: tuple[str, ...] = ("access", "refresh")) -> None:
        now = self._now()
        for kind in kinds:
            conn.execute(
                "UPDATE hbbs1_tokens SET revoked_at = ? WHERE account = ? AND kind = ? AND revoked_at IS NULL",
                (now, account, kind),
            )

    def _token_by_digest(self, conn: Any, token: str, kind: str, field_name: str = "args.token") -> Any:
        if not isinstance(token, str) or not (32 <= len(token) <= 512):
            raise _error("token_invalid", field=field_name)
        row = conn.execute(
            "SELECT * FROM hbbs1_tokens WHERE digest = ? AND kind = ?",
            (token_digest(token), kind),
        ).fetchone()
        if row is None:
            raise _error("token_invalid", field=field_name)
        return row

    def _token_row(self, conn: Any, token: str, kind: str, field_name: str = "args.token") -> Any:
        row = self._token_by_digest(conn, token, kind, field_name)
        if row["revoked_at"] is not None:
            raise _error("token_invalid", field=field_name)
        if int(row["expires_at"]) <= self._now():
            raise _error("token_expired", field=field_name)
        return row

    def _status_error(self, conn: Any, row: Any) -> None:
        status = row["status"]
        if status == "banned":
            ban = conn.execute(
                "SELECT * FROM hbbs1_bans WHERE account = ? AND lifted_at IS NULL ORDER BY id DESC LIMIT 1",
                (row["account"],),
            ).fetchone()
            details: dict[str, Any] = {}
            retry = None
            if ban is not None:
                if int(ban["permanent"]):
                    details["permanent"] = True
                elif ban["retry_after"] is not None:
                    retry = int(ban["retry_after"])
            raise _error("account_banned", retry_after=retry, details=details)
        if status == "suspended":
            raise _error("account_suspended")
        if status == "pending":
            raise _error("account_pending")
        if status == "rejected":
            raise _error("account_rejected")
        if status not in {"active", "probation"}:
            raise _error("forbidden")

    def _new_session(self, row: Any, token_row: Any | None = None) -> Session:
        now = self._now()
        expiry = now + ACCESS_TOKEN_TTL
        if token_row is not None:
            expiry = min(expiry, int(token_row["expires_at"]))
        return Session(
            account=row["account"],
            role=row["role"],
            session_id=_new_id("ses_"),
            issued_at=now,
            expires_at=expiry,
            last_activity=now,
            access_digest=token_row["digest"] if token_row is not None else None,
        )

    def check_session(self, session: Session) -> None:
        now = self._now()
        with self.db.connect() as conn:
            row = self._account(conn, session.account)
            if row is None:
                raise _error("account_rejected")
            self._status_error(conn, row)
        if now >= session.expires_at:
            raise _error("token_expired")
        if now - session.last_activity > IDLE_SESSION_TTL:
            raise _error("session_expired")
        session.last_activity = now
        session.role = row["role"]

    # ---------------------------------------------------------------- auth
    def authenticate(self, args: Mapping[str, Any], peer: str | None = None) -> AuthResult:
        action = args.get("action")
        if not isinstance(action, str):
            raise _error("invalid_field", field="args.action")
        if action == "login":
            return self._auth_login(args, peer)
        if action == "refresh":
            return self._auth_refresh(args, peer)
        if action == "signup":
            return self._auth_signup(args, peer)
        if action == "signup_status":
            return self._auth_signup_status(args, peer)
        raise _error("invalid_field", field="args.action")

    def _auth_login(self, args: Mapping[str, Any], peer: str | None) -> AuthResult:
        _check_keys(args, {"action", "token"})
        _require(args, "action", "token")
        self._check_auth_rate(peer, None)
        token = args.get("token")
        now = self._now()
        with self.db.connect() as conn:
            token_row = self._token_by_digest(conn, token, "access")
            row = self._account(conn, token_row["account"])
            if row is None:
                raise _error("token_invalid")
            # Report a ban/suspension before the generic revoked-token error so a
            # banned account learns why its token stopped working.
            self._status_error(conn, row)
            if token_row["revoked_at"] is not None:
                raise _error("token_invalid")
            if int(token_row["expires_at"]) <= now:
                raise _error("token_expired")
            session = self._new_session(row, token_row)
            data = {"grant": "login", **self._session_data(row, session)}
        return AuthResult(data, session, False)

    def _auth_refresh(self, args: Mapping[str, Any], peer: str | None) -> AuthResult:
        _check_keys(args, {"action", "refresh_token"})
        _require(args, "action", "refresh_token")
        self._check_auth_rate(peer, None)
        token = args.get("refresh_token")
        now = self._now()
        with self.db.transaction() as conn:
            token_row = self._token_by_digest(conn, token, "refresh", "args.refresh_token")
            row = self._account(conn, token_row["account"])
            if row is None:
                raise _error("token_invalid")
            self._status_error(conn, row)
            if token_row["revoked_at"] is not None:
                raise _error("token_invalid", field="args.refresh_token")
            if int(token_row["expires_at"]) <= now:
                raise _error("token_expired", field="args.refresh_token")
            conn.execute("UPDATE hbbs1_tokens SET revoked_at = ? WHERE id = ?", (now, token_row["id"]))
            access = self._issue_token(conn, row["account"], "access", ACCESS_TOKEN_TTL, now)
            refresh = self._issue_token(conn, row["account"], "refresh", REFRESH_TOKEN_TTL, now)
            access_row = conn.execute(
                "SELECT * FROM hbbs1_tokens WHERE digest = ?", (token_digest(access),)
            ).fetchone()
            session = self._new_session(row, access_row)
            data = {
                "grant": "refresh",
                **self._session_data(row, session),
                "access_token": access,
                "refresh_token": refresh,
            }
            self._audit(conn, row["account"], "auth.refresh", target_type="account", target_id=row["account"])
        return AuthResult(data, session, False)

    def _auth_signup(self, args: Mapping[str, Any], peer: str | None) -> AuthResult:
        _check_keys(args, {"action", "account", "display_name", "kind", "owner_account"})
        _require(args, "action", "account", "display_name", "kind")
        kind = args.get("kind")
        if kind == "sysop":
            raise _error("field_not_allowed", field="args.kind")
        if kind not in {"human", "agent"}:
            raise _error("invalid_field", field="args.kind")
        account = _account_id(args.get("account"), "args.account")
        if account == "sysop":
            raise _error("invalid_field", field="args.account")
        display_name = _display_name(args.get("display_name"), "args.display_name")
        auto_mode = self.config.signup_mode == "auto"
        owner = args.get("owner_account")
        if kind == "agent":
            if owner is None:
                if not auto_mode:
                    raise _error("owner_required", field="args.owner_account")
            else:
                owner = _account_id(owner, "args.owner_account")
        elif owner is not None:
            raise _error("invalid_field", field="args.owner_account")
        if self.config.signup_mode == "closed":
            raise _error("forbidden", field="args.account")
        self._check_auth_rate(peer, account)
        auto_kind = auto_mode and kind in self.config.auto_approve_kinds
        now = self._now()
        with self.db.transaction() as conn:
            existing = self._account(conn, account)
            if existing is not None:
                if auto_mode and existing["status"] == "banned":
                    raise _error("account_banned", field="args.account")
                if existing["status"] == "pending":
                    raise _error("account_pending", field="args.account")
                if existing["status"] == "rejected":
                    raise _error("account_rejected", field="args.account")
                raise _error("account_exists", field="args.account")
            pending = conn.execute(
                "SELECT * FROM hbbs1_applications WHERE account = ? AND status = 'pending_moderation'",
                (account,),
            ).fetchone()
            if pending is not None:
                raise _error("account_pending", field="args.account")
            owner_eligible = True
            if kind == "agent":
                owner_row = self._account(conn, owner) if owner is not None else None
                owner_eligible = (
                    owner_row is not None
                    and owner_row["kind"] == "human"
                    and owner_row["status"] == "active"
                    and owner_row["role"] in {"human", "sysop"}
                )
                if not owner_eligible and not auto_mode:
                    raise _error("owner_not_eligible", field="args.owner_account")
            approve_now = bool(auto_kind and owner_eligible)
            application_id = _new_id("app_")
            claim = new_token()
            claim_expires = now + CLAIM_TOKEN_TTL
            if approve_now:
                conn.execute(
                    "INSERT INTO hbbs1_applications(application_id, account, display_name, kind, owner_account, status, "
                    "claim_digest, claim_expires_at, queue_position, created_at, decided_at, decided_by) "
                    "VALUES (?, ?, ?, ?, ?, 'approved', ?, ?, 0, ?, ?, 'system:auto')",
                    (
                        application_id,
                        account,
                        display_name,
                        kind,
                        owner if kind == "agent" else None,
                        token_digest(claim),
                        claim_expires,
                        now,
                        now,
                    ),
                )
                conn.execute(
                    "INSERT INTO hbbs1_accounts(account, display_name, kind, role, owner_account, status, attestation_id, created_at, approved_at) "
                    "VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)",
                    (
                        account,
                        display_name,
                        kind,
                        kind,
                        owner if kind == "agent" else None,
                        _new_id("att_"),
                        now,
                        now,
                    ),
                )
                self._audit(
                    conn,
                    None,
                    "account.signup",
                    target_type="application",
                    target_id=application_id,
                    detail={"kind": kind, "owner_required": kind == "agent", "auto_approved": True},
                )
                self._audit(
                    conn,
                    "system:auto",
                    "account.approve",
                    target_type="application",
                    target_id=application_id,
                    detail={"auto": True, "kind": kind},
                )
                application_row = conn.execute(
                    "SELECT * FROM hbbs1_applications WHERE application_id = ?", (application_id,)
                ).fetchone()
                account_row = self._account(conn, account)
                access = self._issue_token(conn, account, "access", ACCESS_TOKEN_TTL, now)
                refresh = self._issue_token(conn, account, "refresh", REFRESH_TOKEN_TTL, now)
                access_row = conn.execute(
                    "SELECT * FROM hbbs1_tokens WHERE digest = ?", (token_digest(access),)
                ).fetchone()
                session = self._new_session(account_row, access_row)
                data = {
                    "grant": "signup",
                    "application": self._application_public(application_row),
                    **self._session_data(account_row, session),
                    "access_token": access,
                    "refresh_token": refresh,
                }
            else:
                queue_position = int(
                    conn.execute(
                        "SELECT COUNT(*) AS n FROM hbbs1_applications WHERE status = 'pending_moderation'"
                    ).fetchone()["n"]
                ) + 1
                conn.execute(
                    "INSERT INTO hbbs1_applications(application_id, account, display_name, kind, owner_account, status, "
                    "claim_digest, claim_expires_at, queue_position, created_at) "
                    "VALUES (?, ?, ?, ?, ?, 'pending_moderation', ?, ?, ?, ?)",
                    (
                        application_id,
                        account,
                        display_name,
                        kind,
                        owner if kind == "agent" else None,
                        token_digest(claim),
                        claim_expires,
                        queue_position,
                        now,
                    ),
                )
                self._audit(
                    conn,
                    None,
                    "account.signup",
                    target_type="application",
                    target_id=application_id,
                    detail={"kind": kind, "owner_required": kind == "agent"},
                )
                data = {
                    "application": self._application_public(
                        {
                            "application_id": application_id,
                            "account": account,
                            "display_name": display_name,
                            "kind": kind,
                            "owner_account": owner if kind == "agent" else None,
                            "status": "pending_moderation",
                            "queue_position": queue_position,
                            "created_at": now,
                        }
                    ),
                    "claim_token": claim,
                    "claim_expires_at": _iso(claim_expires),
                }
        if approve_now:
            return AuthResult(data, session, False)
        return AuthResult(data, None, True)

    def _application_public(self, row: Mapping[str, Any]) -> dict[str, Any]:
        application: dict[str, Any] = {
            "application_id": row["application_id"],
            "account": row["account"],
            "display_name": row["display_name"],
            "kind": row["kind"],
            "status": row["status"],
            "queue_position": int(row["queue_position"]),
            "created_at": _iso(int(row["created_at"])),
            "trust": "untrusted",
        }
        if row["kind"] == "agent":
            application["owner_account"] = row["owner_account"]
        return application

    def _auth_signup_status(self, args: Mapping[str, Any], peer: str | None) -> AuthResult:
        _check_keys(args, {"action", "application_id", "claim_token"})
        _require(args, "action", "application_id", "claim_token")
        application_id = args.get("application_id")
        claim = args.get("claim_token")
        if not isinstance(application_id, str) or re.fullmatch(r"app_[0-9a-z]{16,40}", application_id) is None:
            raise _error("invalid_field", field="args.application_id")
        if not isinstance(claim, str) or not (32 <= len(claim) <= 512):
            raise _error("token_invalid", field="args.claim_token")
        self._check_auth_rate(peer, None)
        now = self._now()
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT * FROM hbbs1_applications WHERE application_id = ?", (application_id,)
            ).fetchone()
            if row is None or row["claim_digest"] != token_digest(claim):
                raise _error("application_not_found", field="args.application_id")
            if int(row["claim_expires_at"]) <= now:
                raise _error("token_expired", field="args.claim_token")
            status = row["status"]
            if status == "rejected":
                raise _error("account_rejected", field="args.application_id")
            if status == "pending_moderation":
                data = {
                    "application": self._application_public(row),
                    "claim_expires_at": _iso(int(row["claim_expires_at"])),
                }
                return AuthResult(data, None, True)
            account_row = self._account(conn, row["account"])
            if account_row is None:
                raise _error("application_not_found", field="args.application_id")
            self._status_error(conn, account_row)
            rotated = new_token()
            conn.execute(
                "UPDATE hbbs1_applications SET claim_digest = ?, claim_expires_at = ? WHERE application_id = ?",
                (token_digest(rotated), now + CLAIM_TOKEN_TTL, application_id),
            )
            access = self._issue_token(conn, account_row["account"], "access", ACCESS_TOKEN_TTL, now)
            refresh = self._issue_token(conn, account_row["account"], "refresh", REFRESH_TOKEN_TTL, now)
            access_row = conn.execute(
                "SELECT * FROM hbbs1_tokens WHERE digest = ?", (token_digest(access),)
            ).fetchone()
            session = self._new_session(account_row, access_row)
            data = {
                "grant": "signup",
                "application": self._application_public(row),
                **self._session_data(account_row, session),
                "access_token": access,
                "refresh_token": refresh,
            }
            self._audit(conn, account_row["account"], "auth.signup_exchange", target_type="application", target_id=application_id)
        return AuthResult(data, session, False)

    # ---------------------------------------------------------------- commands
    def whoami(self, session: Session) -> dict[str, Any]:
        with self.db.connect() as conn:
            row = self._account(conn, session.account)
            if row is None:
                raise _error("account_rejected")
            self._status_error(conn, row)
            return self._session_data(row, session)

    def list_boards(self, session: Session) -> dict[str, Any]:
        return {"boards": [copy.deepcopy(board) for board in BOARDS]}

    def _board(self, board_id: Any) -> dict[str, Any]:
        if not isinstance(board_id, str) or board_id not in _BOARDS:
            raise _error("board_not_found", field="args.board")
        return _BOARDS[board_id]

    def _thread_row(self, conn: Any, board_id: str, thread_id: str) -> Any:
        row = conn.execute(
            "SELECT * FROM hbbs1_threads WHERE thread_id = ? AND board_id = ?",
            (thread_id, board_id),
        ).fetchone()
        if row is None:
            raise _error("thread_not_found", field="args.thread_id")
        return row

    def _thread_public(self, conn: Any, row: Any) -> dict[str, Any]:
        author = self._account(conn, row["author_account"])
        if author is None:
            raise _error("internal_error")
        return {
            "thread_id": row["thread_id"],
            "board_id": row["board_id"],
            "subject": row["subject"],
            "author": self._public_account(author, include_attestation=True, issued_at=int(row["created_at"])),
            "created_at": _iso(int(row["created_at"])),
            "last_activity_at": _iso(int(row["last_activity_at"])),
            "reply_count": int(row["reply_count"]),
            "status": row["status"],
            "trust": "untrusted",
        }

    def _post_full(self, conn: Any, row: Any) -> dict[str, Any]:
        author = self._account(conn, row["author_account"])
        if author is None:
            raise _error("internal_error")
        post: dict[str, Any] = {
            "post_id": row["post_id"],
            "thread_id": row["thread_id"],
            "board_id": row["board_id"],
            "body": row["body"],
            "author": self._public_account(author, include_attestation=True, issued_at=int(row["created_at"])),
            "created_at": _iso(int(row["created_at"])),
            "status": row["status"],
            "content_hash": row["content_hash"],
            "trust": "untrusted",
        }
        if row["subject"] is not None:
            post["subject"] = row["subject"]
        if row["reply_to_post_id"] is not None:
            post["reply_to_post_id"] = row["reply_to_post_id"]
        return post

    def _post_summary(self, conn: Any, row: Any) -> dict[str, Any]:
        post = self._post_full(conn, row)
        post.pop("body", None)
        post.pop("reply_to_post_id", None)
        post["body_preview"] = row["body"][:160]
        return post

    def _visible(self, row: Any, session: Session) -> bool:
        if row["status"] == "published":
            return True
        if session.role == "sysop":
            return True
        return row["author_account"] == session.account

    def _thread_visible(self, row: Any, session: Session) -> bool:
        if row["status"] == "published":
            return True
        if session.role == "sysop":
            return True
        return row["author_account"] == session.account

    def _cursor_offset(self, cursor: Any) -> int:
        if cursor is None:
            return 0
        if not isinstance(cursor, str) or re.fullmatch(r"off_[0-9]{1,6}", cursor) is None:
            raise _error("invalid_field", field="args.cursor")
        return int(cursor[4:])

    def _limit(self, value: Any, default: int) -> int:
        if value is None:
            return default
        if isinstance(value, bool) or not isinstance(value, int) or not (1 <= value <= 100):
            raise _error("invalid_field", field="args.limit")
        return value

    def list_threads(self, session: Session, args: Mapping[str, Any]) -> dict[str, Any]:
        board = self._board(args.get("board"))
        limit = self._limit(args.get("limit"), 25)
        offset = self._cursor_offset(args.get("cursor"))
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM hbbs1_threads WHERE board_id = ? ORDER BY last_activity_at DESC, thread_id ASC",
                (board["board_id"],),
            ).fetchall()
            visible = [row for row in rows if self._thread_visible(row, session)]
            window = visible[offset : offset + limit + 1]
            threads = [self._thread_public(conn, row) for row in window[:limit]]
        next_cursor = f"off_{offset + limit}" if len(window) > limit else None
        return {"threads": threads, "next_cursor": next_cursor}

    def list_posts(self, session: Session, args: Mapping[str, Any]) -> dict[str, Any]:
        board = self._board(args.get("board"))
        thread_id = args.get("thread_id")
        if not isinstance(thread_id, str):
            raise _error("invalid_field", field="args.thread_id")
        limit = self._limit(args.get("limit"), 25)
        offset = self._cursor_offset(args.get("cursor"))
        with self.db.connect() as conn:
            self._thread_row(conn, board["board_id"], thread_id)
            rows = conn.execute(
                "SELECT * FROM hbbs1_posts WHERE thread_id = ? AND board_id = ? "
                "ORDER BY created_at ASC, post_id ASC",
                (thread_id, board["board_id"]),
            ).fetchall()
            visible = [row for row in rows if self._visible(row, session)]
            window = visible[offset : offset + limit + 1]
            posts = [self._post_summary(conn, row) for row in window[:limit]]
        next_cursor = f"off_{offset + limit}" if len(window) > limit else None
        return {"posts": posts, "next_cursor": next_cursor}

    def read_thread(self, session: Session, args: Mapping[str, Any]) -> dict[str, Any]:
        board = self._board(args.get("board"))
        thread_id = args.get("thread_id")
        if not isinstance(thread_id, str):
            raise _error("invalid_field", field="args.thread_id")
        limit = self._limit(args.get("limit"), 50)
        offset = self._cursor_offset(args.get("cursor"))
        post_id = args.get("post_id")
        if post_id is not None and not isinstance(post_id, str):
            raise _error("invalid_field", field="args.post_id")
        with self.db.connect() as conn:
            thread = self._thread_row(conn, board["board_id"], thread_id)
            if post_id is not None:
                row = conn.execute(
                    "SELECT * FROM hbbs1_posts WHERE post_id = ? AND thread_id = ?",
                    (post_id, thread_id),
                ).fetchone()
                if row is None or not self._visible(row, session):
                    raise _error("post_not_found", field="args.post_id")
                posts = [self._post_full(conn, row)]
                next_cursor = None
            else:
                rows = conn.execute(
                    "SELECT * FROM hbbs1_posts WHERE thread_id = ? AND board_id = ? "
                    "ORDER BY created_at ASC, post_id ASC",
                    (thread_id, board["board_id"]),
                ).fetchall()
                visible = [row for row in rows if self._visible(row, session)]
                window = visible[offset : offset + limit + 1]
                posts = [self._post_full(conn, row) for row in window[:limit]]
                next_cursor = f"off_{offset + limit}" if len(window) > limit else None
            thread_data = self._thread_public(conn, thread)
        return {"thread": thread_data, "posts": posts, "next_cursor": next_cursor}

    # ---------------------------------------------------------------- writes
    def _idempotent(
        self,
        conn: Any,
        account: str,
        client_ref: str | None,
        command: str,
        args: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        if client_ref is None:
            return None
        digest = _args_digest(command, args)
        row = conn.execute(
            "SELECT * FROM hbbs1_idempotency WHERE account = ? AND client_ref = ?",
            (account, client_ref),
        ).fetchone()
        if row is None:
            return None
        if row["command"] != command or row["args_digest"] != digest:
            raise _error("client_ref_conflict", field="args.client_ref")
        result = json.loads(row["result_json"])
        result["idempotent_replay"] = True
        return result

    def _store_idempotent(
        self,
        conn: Any,
        account: str,
        client_ref: str | None,
        command: str,
        args: Mapping[str, Any],
        result: dict[str, Any],
    ) -> None:
        if client_ref is None:
            return
        stored = dict(result)
        stored["idempotent_replay"] = False
        conn.execute(
            "INSERT OR REPLACE INTO hbbs1_idempotency(account, client_ref, command, args_digest, result_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (account, client_ref, command, _args_digest(command, args), json.dumps(stored, sort_keys=True), self._now()),
        )

    def _duplicate(
        self,
        conn: Any,
        account: str,
        board_id: str,
        digest: str,
        window: int,
    ) -> None:
        row = conn.execute(
            "SELECT * FROM hbbs1_duplicates WHERE account = ? AND board_id = ? AND content_hash = ?",
            (account, board_id, digest),
        ).fetchone()
        now = self._now()
        if row is not None and now - int(row["created_at"]) < window:
            retry = max(1, window - (now - int(row["created_at"])))
            raise _error(
                "duplicate_content",
                retry_after=retry,
                details={"original_post_id": row["post_id"], "window_seconds": window},
            )

    def _record_duplicate(self, conn: Any, account: str, board_id: str, digest: str, post_id: str) -> None:
        conn.execute(
            "INSERT OR REPLACE INTO hbbs1_duplicates(account, board_id, content_hash, post_id, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (account, board_id, digest, post_id, self._now()),
        )

    def _body_limit(self, role: str, board: Mapping[str, Any]) -> int:
        role_limit = int(self.limits.get(role, self.limits["human"])["write"]["max_body_bytes"])
        return min(role_limit, int(board["max_body_bytes"]), 8192)

    def _write_status(self, row: Any) -> str:
        if self.config.post_moderation or row["status"] == "probation":
            return "pending"
        return "published"

    def create_post(self, session: Session, args: Mapping[str, Any]) -> dict[str, Any]:
        board = self._board(args.get("board"))
        subject = _text(args.get("subject"), "args.subject", max_chars=120, allow_lf=False)
        body = _text(args.get("body"), "args.body", max_chars=8192, allow_lf=True)
        client_ref = _client_ref(args.get("client_ref"))
        max_body = self._body_limit(session.role, board)
        if len(body.encode("ascii")) > max_body:
            raise _error("content_too_large", field="args.body", details={"limit": max_body})
        now = self._now()
        with self.db.transaction() as conn:
            row = self._account(conn, session.account)
            if row is None:
                raise _error("account_rejected")
            self._status_error(conn, row)
            if session.role not in board["post_roles"]:
                raise _error("read_only_board", field="args.board", details={"board_id": board["board_id"]})
            replay = self._idempotent(conn, session.account, client_ref, "POST", args)
            if replay is not None:
                return replay
            digest = content_hash(session.account, board["board_id"], "new", subject, body)
            window = int(self.limits.get(session.role, self.limits["human"])["write"]["duplicate_window_seconds"])
            self._duplicate(conn, session.account, board["board_id"], digest, window)
            self._check_windows(self._write_hits(session, board["board_id"], None))
            thread_id = _new_id("thr_")
            post_id = _new_id("pst_")
            status = self._write_status(row)
            conn.execute(
                "INSERT INTO hbbs1_threads(thread_id, board_id, subject, author_account, created_at, last_activity_at, reply_count, status) "
                "VALUES (?, ?, ?, ?, ?, ?, 0, ?)",
                (thread_id, board["board_id"], subject, session.account, now, now, status),
            )
            conn.execute(
                "INSERT INTO hbbs1_posts(post_id, thread_id, board_id, author_account, subject, body, created_at, status, content_hash, client_ref) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (post_id, thread_id, board["board_id"], session.account, subject, body, now, status, digest, client_ref),
            )
            self._record_duplicate(conn, session.account, board["board_id"], digest, post_id)
            if status == "pending":
                conn.execute(
                    "INSERT INTO hbbs1_modqueue(kind, target_id, state, reason, created_at) "
                    "VALUES ('post', ?, 'pending', 'premoderation', ?)",
                    (post_id, now),
                )
            self._audit(
                conn,
                session.account,
                "post.create",
                target_type="post",
                target_id=post_id,
                detail={"board": board["board_id"], "status": status, "body_len": len(body)},
            )
            thread_row = conn.execute("SELECT * FROM hbbs1_threads WHERE thread_id = ?", (thread_id,)).fetchone()
            post_row = conn.execute("SELECT * FROM hbbs1_posts WHERE post_id = ?", (post_id,)).fetchone()
            result = {
                "post": self._post_full(conn, post_row),
                "thread": self._thread_public(conn, thread_row),
                "idempotent_replay": False,
            }
            self._store_idempotent(conn, session.account, client_ref, "POST", args, result)
            return result

    def create_reply(self, session: Session, args: Mapping[str, Any]) -> dict[str, Any]:
        board = self._board(args.get("board"))
        thread_id = args.get("thread_id")
        if not isinstance(thread_id, str):
            raise _error("invalid_field", field="args.thread_id")
        body = _text(args.get("body"), "args.body", max_chars=8192, allow_lf=True)
        client_ref = _client_ref(args.get("client_ref"))
        reply_to = args.get("reply_to_post_id")
        if reply_to is not None and not isinstance(reply_to, str):
            raise _error("invalid_field", field="args.reply_to_post_id")
        max_body = self._body_limit(session.role, board)
        if len(body.encode("ascii")) > max_body:
            raise _error("content_too_large", field="args.body", details={"limit": max_body})
        now = self._now()
        with self.db.transaction() as conn:
            row = self._account(conn, session.account)
            if row is None:
                raise _error("account_rejected")
            self._status_error(conn, row)
            if session.role not in board["reply_roles"]:
                raise _error("read_only_board", field="args.board", details={"board_id": board["board_id"]})
            thread = self._thread_row(conn, board["board_id"], thread_id)
            if reply_to is not None:
                target = conn.execute(
                    "SELECT * FROM hbbs1_posts WHERE post_id = ? AND thread_id = ?",
                    (reply_to, thread_id),
                ).fetchone()
                if target is None:
                    raise _error("post_not_found", field="args.reply_to_post_id")
            replay = self._idempotent(conn, session.account, client_ref, "REPLY", args)
            if replay is not None:
                return replay
            digest = content_hash(session.account, board["board_id"], thread_id, "", body)
            window = int(self.limits.get(session.role, self.limits["human"])["write"]["duplicate_window_seconds"])
            self._duplicate(conn, session.account, board["board_id"], digest, window)
            self._check_windows(self._write_hits(session, board["board_id"], thread_id))
            post_id = _new_id("pst_")
            status = self._write_status(row)
            conn.execute(
                "INSERT INTO hbbs1_posts(post_id, thread_id, board_id, author_account, subject, body, created_at, status, content_hash, reply_to_post_id, client_ref) "
                "VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)",
                (post_id, thread_id, board["board_id"], session.account, body, now, status, digest, reply_to, client_ref),
            )
            conn.execute(
                "UPDATE hbbs1_threads SET last_activity_at = ?, reply_count = reply_count + 1 WHERE thread_id = ?",
                (now, thread_id),
            )
            if status == "pending":
                conn.execute(
                    "INSERT INTO hbbs1_modqueue(kind, target_id, state, reason, created_at) "
                    "VALUES ('post', ?, 'pending', 'premoderation', ?)",
                    (post_id, now),
                )
            self._record_duplicate(conn, session.account, board["board_id"], digest, post_id)
            self._audit(
                conn,
                session.account,
                "post.reply",
                target_type="post",
                target_id=post_id,
                detail={"board": board["board_id"], "thread_id": thread_id, "status": status, "body_len": len(body)},
            )
            post_row = conn.execute("SELECT * FROM hbbs1_posts WHERE post_id = ?", (post_id,)).fetchone()
            thread_row = conn.execute("SELECT * FROM hbbs1_threads WHERE thread_id = ?", (thread_id,)).fetchone()
            result = {
                "post": self._post_full(conn, post_row),
                "thread": self._thread_public(conn, thread_row),
                "idempotent_replay": False,
            }
            self._store_idempotent(conn, session.account, client_ref, "REPLY", args, result)
            return result

    # ---------------------------------------------------------------- mail
    def _message_public(self, conn: Any, row: Any, *, include_body: bool = False) -> dict[str, Any]:
        sender = self._account(conn, row["sender"])
        if sender is None:
            raise _error("internal_error")
        message: dict[str, Any] = {
            "message_id": row["message_id"],
            "from": self._public_account(sender, include_attestation=True, issued_at=int(row["created_at"])),
            "to": row["recipient"],
            "subject": row["subject"],
            "created_at": _iso(int(row["created_at"])),
            "read": row["read_at"] is not None,
            "kind": row["kind"],
            "trust": "untrusted",
        }
        if row["kind"] == "report" and row["target_type"] and row["target_id"]:
            message["target"] = {"target_type": row["target_type"], "target_id": row["target_id"]}
        if include_body:
            message["body"] = row["body"]
        return message

    def mail(self, session: Session, args: Mapping[str, Any]) -> dict[str, Any]:
        action = args.get("action")
        if action == "send":
            return self._mail_send(session, args)
        if action == "list":
            return self._mail_list(session, args)
        if action == "read":
            return self._mail_read(session, args)
        raise _error("invalid_field", field="args.action")

    def _mail_send(self, session: Session, args: Mapping[str, Any]) -> dict[str, Any]:
        kind = args.get("kind")
        client_ref = _client_ref(args.get("client_ref"))
        now = self._now()
        if kind == "message":
            to = args.get("to")
            if to != "sysop":
                to = _account_id(to, "args.to")
            subject = _text(args.get("subject"), "args.subject", max_chars=120, allow_lf=False)
            body = _text(args.get("body"), "args.body", max_chars=8192, allow_lf=True)
            max_body = int(self.limits.get(session.role, self.limits["human"])["write"]["max_body_bytes"])
            if len(body.encode("ascii")) > max_body:
                raise _error("content_too_large", field="args.body", details={"limit": max_body})
            with self.db.transaction() as conn:
                row = self._account(conn, session.account)
                if row is None:
                    raise _error("account_rejected")
                self._status_error(conn, row)
                if to != "sysop":
                    recipient = self._account(conn, to)
                    if recipient is None or recipient["status"] not in {"active", "probation"}:
                        raise _error("message_not_found", field="args.to")
                replay = self._idempotent(conn, session.account, client_ref, "MAIL", args)
                if replay is not None:
                    return replay
                self._check_windows(self._write_hits(session, "mail", None))
                message_id = _new_id("msg_")
                conn.execute(
                    "INSERT INTO hbbs1_messages(message_id, sender, recipient, kind, subject, body, created_at, status) "
                    "VALUES (?, ?, ?, 'message', ?, ?, ?, 'delivered')",
                    (message_id, session.account, to, subject, body, now),
                )
                self._audit(conn, session.account, "mail.send", target_type="message", target_id=message_id)
                result = {
                    "message_id": message_id,
                    "kind": "message",
                    "status": "delivered",
                    "created_at": _iso(now),
                }
                self._store_idempotent(conn, session.account, client_ref, "MAIL", args, result)
                return result
        if kind == "report":
            target_type = args.get("target_type")
            if target_type not in {"post", "thread", "mail", "account"}:
                raise _error("invalid_field", field="args.target_type")
            target_id = args.get("target_id")
            target_patterns = {
                "post": r"pst_[0-9a-z]{16,40}",
                "thread": r"thr_[0-9a-z]{16,40}",
                "mail": r"msg_[0-9a-z]{16,40}",
                "account": r"[a-z0-9][a-z0-9_.-]{2,31}",
            }
            if not isinstance(target_id, str) or re.fullmatch(target_patterns[target_type], target_id) is None:
                raise _error("invalid_field", field="args.target_id")
            reason = _text(args.get("reason"), "args.reason", max_chars=500, allow_lf=True)
            with self.db.transaction() as conn:
                row = self._account(conn, session.account)
                if row is None:
                    raise _error("account_rejected")
                self._status_error(conn, row)
                replay = self._idempotent(conn, session.account, client_ref, "MAIL", args)
                if replay is not None:
                    return replay
                self._check_windows(self._write_hits(session, "mail", None))
                message_id = _new_id("msg_")
                subject = f"Report: {target_type} {target_id}"[:120]
                conn.execute(
                    "INSERT INTO hbbs1_messages(message_id, sender, recipient, kind, subject, body, target_type, target_id, created_at, status) "
                    "VALUES (?, ?, 'sysop', 'report', ?, ?, ?, ?, ?, 'queued')",
                    (message_id, session.account, subject, reason, target_type, target_id, now),
                )
                conn.execute(
                    "INSERT INTO hbbs1_reports(message_id, reporter, target_type, target_id, created_at, state) "
                    "VALUES (?, ?, ?, ?, ?, 'open')",
                    (message_id, session.account, target_type, target_id, now),
                )
                self._audit(
                    conn,
                    session.account,
                    "mail.report",
                    target_type=target_type,
                    target_id=target_id,
                    detail={"message_id": message_id, "reason_len": len(reason)},
                )
                result = {
                    "message_id": message_id,
                    "kind": "report",
                    "status": "queued",
                    "created_at": _iso(now),
                }
                self._store_idempotent(conn, session.account, client_ref, "MAIL", args, result)
                return result
        raise _error("invalid_field", field="args.kind")

    def _mail_list(self, session: Session, args: Mapping[str, Any]) -> dict[str, Any]:
        folder = args.get("folder")
        if folder not in {"inbox", "sent"}:
            raise _error("invalid_field", field="args.folder")
        limit = self._limit(args.get("limit"), 20)
        offset = self._cursor_offset(args.get("cursor"))
        with self.db.connect() as conn:
            if folder == "inbox" and session.role == "sysop":
                rows = conn.execute(
                    "SELECT * FROM hbbs1_messages WHERE recipient IN (?, 'sysop') "
                    "ORDER BY created_at DESC, message_id DESC LIMIT ? OFFSET ?",
                    (session.account, limit + 1, offset),
                ).fetchall()
            else:
                column = "recipient" if folder == "inbox" else "sender"
                rows = conn.execute(
                    f"SELECT * FROM hbbs1_messages WHERE {column} = ? "
                    "ORDER BY created_at DESC, message_id DESC LIMIT ? OFFSET ?",
                    (session.account, limit + 1, offset),
                ).fetchall()
            messages = [self._message_public(conn, row) for row in rows[:limit]]
        next_cursor = f"off_{offset + limit}" if len(rows) > limit else None
        return {"messages": messages, "next_cursor": next_cursor}

    def _mail_read(self, session: Session, args: Mapping[str, Any]) -> dict[str, Any]:
        message_id = args.get("message_id")
        if not isinstance(message_id, str):
            raise _error("invalid_field", field="args.message_id")
        with self.db.transaction() as conn:
            row = conn.execute("SELECT * FROM hbbs1_messages WHERE message_id = ?", (message_id,)).fetchone()
            if row is None:
                raise _error("message_not_found", field="args.message_id")
            allowed = session.account in {row["sender"], row["recipient"]} or session.role == "sysop"
            if not allowed:
                raise _error("message_not_found", field="args.message_id")
            if row["recipient"] == session.account and row["read_at"] is None and session.role != "sysop":
                conn.execute("UPDATE hbbs1_messages SET read_at = ? WHERE message_id = ?", (self._now(), message_id))
                row = conn.execute("SELECT * FROM hbbs1_messages WHERE message_id = ?", (message_id,)).fetchone()
            return {"message": self._message_public(conn, row, include_body=True)}

    def logout(self, session: Session, args: Mapping[str, Any]) -> dict[str, Any]:
        revoke_refresh = bool(args.get("revoke_refresh", False))
        with self.db.transaction() as conn:
            if session.access_digest:
                conn.execute(
                    "UPDATE hbbs1_tokens SET revoked_at = ? WHERE digest = ? AND revoked_at IS NULL",
                    (self._now(), session.access_digest),
                )
            if revoke_refresh:
                self._revoke_tokens(conn, session.account, kinds=("refresh",))
            self._audit(conn, session.account, "auth.logout", target_type="account", target_id=session.account)
        return {"revoked": True, "all_sessions": False}

    # ---------------------------------------------------------------- admin
    def bootstrap_sysop(self, account: str, display_name: str | None = None) -> dict[str, Any]:
        account = account.strip().lower()
        if ACCOUNT_RE.fullmatch(account) is None:
            raise ValueError("sysop account is not a valid HBBS/1 account id")
        display_name = display_name or account
        if DISPLAY_RE.fullmatch(display_name) is None:
            raise ValueError("sysop display name is not valid")
        now = self._now()
        with self.db.transaction() as conn:
            row = self._account(conn, account)
            if row is None:
                conn.execute(
                    "INSERT INTO hbbs1_accounts(account, display_name, kind, role, owner_account, status, attestation_id, created_at, approved_at) "
                    "VALUES (?, ?, 'human', 'sysop', NULL, 'active', ?, ?, ?)",
                    (account, display_name, _new_id("att_"), now, now),
                )
                self._audit(conn, None, "account.bootstrap_sysop", target_type="account", target_id=account)
            elif row["role"] != "sysop":
                raise ValueError("configured sysop account already exists with another role")
            return self._public_account(self._account(conn, account))

    def create_account(
        self,
        account: str,
        display_name: str,
        *,
        kind: str = "human",
        role: str | None = None,
        owner_account: str | None = None,
        status: str = "active",
    ) -> dict[str, Any]:
        """Create an active account directly (admin/tests; not a wire command)."""
        account = account.strip().lower()
        if ACCOUNT_RE.fullmatch(account) is None:
            raise ValueError("invalid account id")
        if DISPLAY_RE.fullmatch(display_name) is None:
            raise ValueError("invalid display name")
        role = role or kind
        if kind not in {"human", "agent"}:
            raise ValueError("kind must be human or agent")
        if role not in {"human", "agent", "sysop"}:
            raise ValueError("invalid role")
        if kind == "agent" and role != "agent":
            raise ValueError("agent accounts cannot hold the sysop role")
        if kind == "human" and role not in {"human", "sysop"}:
            raise ValueError("human accounts cannot hold the agent role")
        if kind == "agent" and not owner_account:
            raise ValueError("agent accounts need an owner")
        now = self._now()
        with self.db.transaction() as conn:
            if self._account(conn, account) is not None:
                raise ValueError("account already exists")
            if kind == "agent":
                owner_row = self._account(conn, owner_account)
                if owner_row is None or owner_row["kind"] != "human" or owner_row["status"] != "active" or owner_row["role"] not in {"human", "sysop"}:
                    raise ValueError("agent owner must be an active human account")
            conn.execute(
                "INSERT INTO hbbs1_accounts(account, display_name, kind, role, owner_account, status, attestation_id, created_at, approved_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (account, display_name, kind, role, owner_account, status, _new_id("att_"), now, now if status == "active" else None),
            )
            self._audit(conn, None, "account.create", target_type="account", target_id=account, detail={"kind": kind, "role": role})
            return self._public_account(self._account(conn, account))

    def issue_access_token(self, account: str, *, ttl: int = ACCESS_TOKEN_TTL) -> str:
        with self.db.transaction() as conn:
            row = self._account(conn, account)
            if row is None:
                raise ValueError("unknown account")
            return self._issue_token(conn, account, "access", ttl, self._now())

    def issue_refresh_token(self, account: str, *, ttl: int = REFRESH_TOKEN_TTL) -> str:
        with self.db.transaction() as conn:
            row = self._account(conn, account)
            if row is None:
                raise ValueError("unknown account")
            return self._issue_token(conn, account, "refresh", ttl, self._now())

    def moderate_application(self, application_id: str, *, approve: bool, actor: str, reason: str | None = None) -> dict[str, Any]:
        actor_row = self._account_actor(actor, require_sysop=True)
        now = self._now()
        with self.db.transaction() as conn:
            app = conn.execute(
                "SELECT * FROM hbbs1_applications WHERE application_id = ?", (application_id,)
            ).fetchone()
            if app is None:
                raise _error("application_not_found", field="args.application_id")
            if app["status"] != "pending_moderation":
                raise _error("forbidden", field="args.application_id")
            new_status = "approved" if approve else "rejected"
            conn.execute(
                "UPDATE hbbs1_applications SET status = ?, queue_position = 0, decided_at = ?, decided_by = ? WHERE application_id = ?",
                (new_status, now, actor, application_id),
            )
            if approve:
                if app["kind"] == "agent":
                    owner = self._account(conn, app["owner_account"])
                    if owner is None or owner["kind"] != "human" or owner["status"] != "active" or owner["role"] not in {"human", "sysop"}:
                        raise _error("owner_not_eligible", field="args.owner_account")
                existing = self._account(conn, app["account"])
                if existing is None:
                    conn.execute(
                        "INSERT INTO hbbs1_accounts(account, display_name, kind, role, owner_account, status, attestation_id, created_at, approved_at) "
                        "VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)",
                        (
                            app["account"],
                            app["display_name"],
                            app["kind"],
                            app["kind"],
                            app["owner_account"],
                            _new_id("att_"),
                            int(app["created_at"]),
                            now,
                        ),
                    )
                else:
                    conn.execute(
                        "UPDATE hbbs1_accounts SET status = 'active', approved_at = ? WHERE account = ?",
                        (now, app["account"]),
                    )
            self._audit(
                conn,
                actor,
                "account.approve" if approve else "account.reject",
                target_type="application",
                target_id=application_id,
                detail={"reason_len": len(reason or "")},
            )
            row = conn.execute(
                "SELECT * FROM hbbs1_applications WHERE application_id = ?", (application_id,)
            ).fetchone()
            return self._application_public(row)

    def ban_account(
        self,
        account: str,
        *,
        actor: str,
        reason: str | None = None,
        permanent: bool = True,
        retry_after: int | None = None,
    ) -> dict[str, Any]:
        self._account_actor(actor, require_sysop=True)
        if account == actor:
            raise _error("forbidden", field="args.account")
        now = self._now()
        with self.db.transaction() as conn:
            row = self._account(conn, account)
            if row is None:
                raise _error("account_rejected", field="args.account")
            if row["role"] == "sysop":
                raise _error("forbidden", field="args.account")
            conn.execute("UPDATE hbbs1_accounts SET status = 'banned' WHERE account = ?", (account,))
            self._revoke_tokens(conn, account)
            conn.execute(
                "INSERT INTO hbbs1_bans(account, actor, reason_len, permanent, retry_after, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (account, actor, len(reason or ""), 1 if permanent else 0, retry_after, now),
            )
            if row["kind"] == "human":
                owned = conn.execute(
                    "SELECT account FROM hbbs1_accounts WHERE kind = 'agent' AND owner_account = ?", (account,)
                ).fetchall()
                for agent in owned:
                    conn.execute("UPDATE hbbs1_accounts SET status = 'suspended' WHERE account = ?", (agent["account"],))
                    self._revoke_tokens(conn, agent["account"])
            self._audit(conn, actor, "account.ban", target_type="account", target_id=account, detail={"permanent": permanent})
            return {"account": self._public_account(self._account(conn, account))}

    def unban_account(self, account: str, *, actor: str) -> dict[str, Any]:
        self._account_actor(actor, require_sysop=True)
        now = self._now()
        with self.db.transaction() as conn:
            row = self._account(conn, account)
            if row is None:
                raise _error("account_rejected", field="args.account")
            conn.execute("UPDATE hbbs1_accounts SET status = 'active' WHERE account = ?", (account,))
            conn.execute(
                "UPDATE hbbs1_bans SET lifted_at = ?, lifted_by = ? WHERE account = ? AND lifted_at IS NULL",
                (now, actor, account),
            )
            conn.execute(
                "UPDATE hbbs1_accounts SET status = 'active' WHERE kind = 'agent' AND owner_account = ? AND status = 'suspended'",
                (account,),
            )
            self._audit(conn, actor, "account.unban", target_type="account", target_id=account)
            return {"account": self._public_account(self._account(conn, account))}

    def reassign_owner(self, agent: str, new_owner: str, *, actor: str) -> dict[str, Any]:
        self._account_actor(actor, require_sysop=True)
        with self.db.transaction() as conn:
            agent_row = self._account(conn, agent)
            owner_row = self._account(conn, new_owner)
            if agent_row is None or agent_row["kind"] != "agent":
                raise _error("forbidden", field="args.agent")
            if owner_row is None or owner_row["kind"] != "human" or owner_row["status"] != "active" or owner_row["role"] not in {"human", "sysop"}:
                raise _error("owner_not_eligible", field="args.owner_account")
            conn.execute("UPDATE hbbs1_accounts SET owner_account = ? WHERE account = ?", (new_owner, agent))
            if agent_row["status"] == "suspended":
                conn.execute("UPDATE hbbs1_accounts SET status = 'active' WHERE account = ?", (agent,))
            self._audit(
                conn,
                actor,
                "account.reassign_owner",
                target_type="account",
                target_id=agent,
                detail={"new_owner": new_owner},
            )
            return {"account": self._public_account(self._account(conn, agent))}

    def _account_actor(self, actor: str, *, require_sysop: bool = False) -> Any:
        with self.db.connect() as conn:
            row = self._account(conn, actor)
            if row is None or row["status"] != "active":
                raise _error("forbidden")
            if require_sysop and row["role"] != "sysop":
                raise _error("forbidden")
            return row

    def list_modqueue(self, *, state: str = "pending") -> dict[str, Any]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM hbbs1_modqueue WHERE state = ? ORDER BY id ASC", (state,)
            ).fetchall()
            items = []
            for row in rows:
                item: dict[str, Any] = {
                    "id": int(row["id"]),
                    "kind": row["kind"],
                    "target_id": row["target_id"],
                    "state": row["state"],
                    "created_at": _iso(int(row["created_at"])),
                }
                if row["kind"] == "post":
                    post = conn.execute(
                        "SELECT * FROM hbbs1_posts WHERE post_id = ?", (row["target_id"],)
                    ).fetchone()
                    if post is not None:
                        item["post"] = self._post_full(conn, post)
                items.append(item)
            return {"items": items}

    def resolve_modqueue(self, item_id: int, *, approve: bool, actor: str, reason: str | None = None) -> dict[str, Any]:
        self._account_actor(actor, require_sysop=True)
        now = self._now()
        with self.db.transaction() as conn:
            item = conn.execute("SELECT * FROM hbbs1_modqueue WHERE id = ?", (int(item_id),)).fetchone()
            if item is None or item["state"] != "pending":
                raise _error("forbidden", field="args.item_id")
            new_state = "approved" if approve else "rejected"
            conn.execute(
                "UPDATE hbbs1_modqueue SET state = ?, resolved_by = ?, resolved_at = ? WHERE id = ?",
                (new_state, actor, now, int(item_id)),
            )
            if item["kind"] == "post":
                post_status = "published" if approve else "removed"
                post = conn.execute(
                    "SELECT * FROM hbbs1_posts WHERE post_id = ?", (item["target_id"],)
                ).fetchone()
                if post is not None:
                    conn.execute("UPDATE hbbs1_posts SET status = ? WHERE post_id = ?", (post_status, post["post_id"]))
                    if post["reply_to_post_id"] is None:
                        conn.execute(
                            "UPDATE hbbs1_threads SET status = ? WHERE thread_id = ?",
                            (post_status, post["thread_id"]),
                        )
            self._audit(
                conn,
                actor,
                "queue.approve" if approve else "queue.reject",
                target_type=item["kind"],
                target_id=item["target_id"],
                detail={"item_id": int(item_id), "reason_len": len(reason or "")},
            )
            return {"item_id": int(item_id), "state": new_state}

    def list_applications(self, *, status: str = "pending_moderation") -> dict[str, Any]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM hbbs1_applications WHERE status = ? ORDER BY created_at ASC", (status,)
            ).fetchall()
            return {"applications": [self._application_public(row) for row in rows]}

    def list_reports(self, *, state: str = "open") -> dict[str, Any]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM hbbs1_reports WHERE state = ? ORDER BY id ASC", (state,)
            ).fetchall()
            reports = []
            for row in rows:
                message = conn.execute(
                    "SELECT * FROM hbbs1_messages WHERE message_id = ?", (row["message_id"],)
                ).fetchone()
                reports.append(
                    {
                        "id": int(row["id"]),
                        "message_id": row["message_id"],
                        "reporter": row["reporter"],
                        "target_type": row["target_type"],
                        "target_id": row["target_id"],
                        "created_at": _iso(int(row["created_at"])),
                        "state": row["state"],
                        "message": self._message_public(conn, message, include_body=True) if message else None,
                    }
                )
            return {"reports": reports}

    def resolve_report(self, report_id: int, *, action: str, actor: str) -> dict[str, Any]:
        self._account_actor(actor, require_sysop=True)
        if action not in {"hide", "dismiss"}:
            raise _error("invalid_field", field="args.action")
        now = self._now()
        with self.db.transaction() as conn:
            report = conn.execute("SELECT * FROM hbbs1_reports WHERE id = ?", (int(report_id),)).fetchone()
            if report is None:
                raise _error("post_not_found", field="args.report_id")
            if report["state"] != "open":
                raise _error("forbidden", field="args.report_id")
            new_state = "resolved" if action == "hide" else "dismissed"
            conn.execute(
                "UPDATE hbbs1_reports SET state = ?, resolved_by = ?, resolved_at = ? WHERE id = ?",
                (new_state, actor, now, int(report_id)),
            )
            post_status = None
            if action == "hide" and report["target_type"] == "post":
                post = conn.execute("SELECT * FROM hbbs1_posts WHERE post_id = ?", (report["target_id"],)).fetchone()
                if post is not None:
                    post_status = "hidden"
                    conn.execute("UPDATE hbbs1_posts SET status = 'hidden' WHERE post_id = ?", (report["target_id"],))
                    conn.execute("UPDATE hbbs1_threads SET status = 'hidden' WHERE thread_id = ?", (post["thread_id"],))
            elif action == "hide" and report["target_type"] == "thread":
                thread = conn.execute("SELECT * FROM hbbs1_threads WHERE thread_id = ?", (report["target_id"],)).fetchone()
                if thread is not None:
                    post_status = "hidden"
                    conn.execute("UPDATE hbbs1_threads SET status = 'hidden' WHERE thread_id = ?", (report["target_id"],))
                    conn.execute("UPDATE hbbs1_posts SET status = 'hidden' WHERE thread_id = ?", (report["target_id"],))
            self._audit(
                conn,
                actor,
                f"report.{action}",
                target_type=report["target_type"],
                target_id=report["target_id"],
                detail={"report_id": int(report_id), "post_status": post_status},
            )
            return {"report_id": int(report_id), "state": new_state, "post_status": post_status}

    def hide_post(self, post_id: str, *, actor: str, reason: str | None = None) -> dict[str, Any]:
        self._account_actor(actor, require_sysop=True)
        with self.db.transaction() as conn:
            post = conn.execute("SELECT * FROM hbbs1_posts WHERE post_id = ?", (post_id,)).fetchone()
            if post is None:
                raise _error("post_not_found", field="args.post_id")
            conn.execute("UPDATE hbbs1_posts SET status = 'hidden' WHERE post_id = ?", (post_id,))
            conn.execute("UPDATE hbbs1_threads SET status = 'hidden' WHERE thread_id = ?", (post["thread_id"],))
            self._audit(
                conn,
                actor,
                "post.hide",
                target_type="post",
                target_id=post_id,
                detail={"reason_len": len(reason or "")},
            )
            return {"post_id": post_id, "status": "hidden"}

    def list_audit(self, *, limit: int = 100) -> dict[str, Any]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM hbbs1_audit ORDER BY id DESC LIMIT ?", (max(1, min(500, int(limit))),)
            ).fetchall()
            entries = [
                {
                    "id": int(row["id"]),
                    "created_at": _iso(int(row["created_at"])),
                    "actor": row["actor"],
                    "action": row["action"],
                    "target_type": row["target_type"],
                    "target_id": row["target_id"],
                    "detail": json.loads(row["detail"] or "{}"),
                }
                for row in rows
            ]
            return {"entries": entries}


class BBS1Connection:
    """Per-connection protocol state.

    One connection carries at most one AUTH. A successful login/refresh binds a
    session to this object; sign-up and pending-status exchanges return and the
    server closes the connection.
    """

    def __init__(self, service: BBS1Service, *, peer: str | None = None) -> None:
        self.service = service
        self.peer = peer
        self.session: Session | None = None
        self.auth_used = False

    def handle(self, frame: Any) -> tuple[dict[str, Any], bool]:
        command = frame.command
        try:
            validate_envelope(command, frame.body)
            args = frame.body["args"]
            if command == "AUTH":
                self._validate_args(command, args)
                if self.auth_used:
                    raise _error("not_authenticated", field="header.command")
                self.auth_used = True
                result = self.service.authenticate(args, self.peer)
                self.session = result.session
                return {"v": 1, "ok": True, "command": command, "data": result.data}, result.close
            if self.session is None:
                raise _error("not_authenticated", field="header.command")
            if command == "LOGOUT":
                try:
                    self.service.check_session(self.session)
                    self.service.check_request_rate(self.session)
                except BBS1Error as exc:
                    # A banned or expired client must still be able to clear its
                    # local state, as the contract requires.
                    if exc.code not in {"account_banned", "account_suspended"}:
                        raise
                self._validate_args(command, args)
                data = self.service.logout(self.session, args)
                return {"v": 1, "ok": True, "command": command, "data": data}, True
            self.service.check_session(self.session)
            self.service.check_request_rate(self.session)
            self._validate_args(command, args)
            if command == "WHOAMI":
                data = self.service.whoami(self.session)
            elif command == "LIST":
                action = args["action"]
                if action == "boards":
                    data = self.service.list_boards(self.session)
                elif action == "threads":
                    data = self.service.list_threads(self.session, args)
                else:
                    data = self.service.list_posts(self.session, args)
            elif command == "READ":
                data = self.service.read_thread(self.session, args)
            elif command == "POST":
                data = self.service.create_post(self.session, args)
            elif command == "REPLY":
                data = self.service.create_reply(self.session, args)
            elif command == "MAIL":
                data = self.service.mail(self.session, args)
            elif command == "LOGOUT":
                data = self.service.logout(self.session, args)
            else:
                raise _error("unknown_command", field="header.command")
            close = command == "LOGOUT"
            return {"v": 1, "ok": True, "command": command, "data": data}, close
        except BBS1Error as exc:
            close = command == "AUTH" or exc.code in {
                "not_authenticated",
                "token_invalid",
                "token_expired",
                "session_expired",
                "account_banned",
                "account_suspended",
                "bad_version",
                "mismatched_command",
                "malformed_json",
                "not_printable_ascii",
                "bad_length",
                "body_too_large",
                "unknown_command",
            }
            return exc.envelope(command), close
        except Exception:
            # Never disclose an internal path, query, or traceback.
            return _error("internal_error").envelope(command), True

    def _validate_args(self, command: str, args: Mapping[str, Any]) -> None:
        if command == "AUTH":
            action = args.get("action")
            if not isinstance(action, str):
                raise _error("invalid_field", field="args.action")
            allowed = {
                "login": {"action", "token"},
                "signup": {"action", "account", "display_name", "kind", "owner_account"},
                "signup_status": {"action", "application_id", "claim_token"},
                "refresh": {"action", "refresh_token"},
            }
            if action not in allowed:
                raise _error("invalid_field", field="args.action")
            _check_keys(args, allowed[action])
            if action == "login":
                _require(args, "action", "token")
            elif action == "signup":
                _require(args, "action", "account", "display_name", "kind")
            elif action == "signup_status":
                _require(args, "action", "application_id", "claim_token")
            else:
                _require(args, "action", "refresh_token")
            return
        if command == "WHOAMI":
            _check_keys(args, set())
            return
        if command == "LIST":
            action = args.get("action")
            if not isinstance(action, str):
                raise _error("invalid_field", field="args.action")
            if action == "boards":
                _check_keys(args, {"action"})
                _require(args, "action")
            elif action == "threads":
                _check_keys(args, {"action", "board", "cursor", "limit"})
                _require(args, "action", "board")
            elif action == "posts":
                _check_keys(args, {"action", "board", "thread_id", "cursor", "limit"})
                _require(args, "action", "board", "thread_id")
            else:
                raise _error("invalid_field", field="args.action")
            return
        if command == "READ":
            _check_keys(args, {"board", "thread_id", "post_id", "cursor", "limit"})
            _require(args, "board", "thread_id")
            return
        if command == "POST":
            _check_keys(args, {"board", "subject", "body", "client_ref"})
            _require(args, "board", "subject", "body")
            return
        if command == "REPLY":
            _check_keys(args, {"board", "thread_id", "reply_to_post_id", "body", "client_ref"})
            _require(args, "board", "thread_id", "body")
            return
        if command == "MAIL":
            action = args.get("action")
            if action == "send":
                kind = args.get("kind")
                if kind == "message":
                    _check_keys(args, {"action", "kind", "to", "subject", "body", "client_ref"})
                    _require(args, "action", "kind", "to", "subject", "body")
                elif kind == "report":
                    _check_keys(args, {"action", "kind", "target_type", "target_id", "reason", "client_ref"})
                    _require(args, "action", "kind", "target_type", "target_id", "reason")
                else:
                    raise _error("invalid_field", field="args.kind")
            elif action == "list":
                _check_keys(args, {"action", "folder", "cursor", "limit"})
                _require(args, "action", "folder")
            elif action == "read":
                _check_keys(args, {"action", "message_id"})
                _require(args, "action", "message_id")
            else:
                raise _error("invalid_field", field="args.action")
            return
        if command == "LOGOUT":
            _check_keys(args, {"revoke_refresh"})
            if "revoke_refresh" in args and not isinstance(args["revoke_refresh"], bool):
                raise _error("invalid_field", field="args.revoke_refresh")
            return
        raise _error("unknown_command", field="header.command")
