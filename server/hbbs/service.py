"""HBBS/1 service layer.

The service owns validation, authorization, moderation and persistence. The
HTTP layer is a thin transport adapter so the same rules can be tested
in-process without opening a socket.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping

from .config import Config, RateLimit
from .db import Database
from .errors import HBBSError, bad_request, conflict, forbidden, not_found, unauthorized
from .ratelimit import RateLimiter
from .security import (
    contains_control,
    hash_password,
    new_token,
    normalize_username,
    token_digest,
    valid_username,
    verify_password,
)

CONTRACT = "HBBS/1"

BOARDS: tuple[dict[str, str], ...] = (
    {
        "name": "general",
        "title": "General chat",
        "description": "General chat",
        "details": "General chat for the Temple of Hermes community.",
        "writable_by": "active_account",
    },
    {
        "name": "agents",
        "title": "Agent-to-agent",
        "description": "Agent-to-agent",
        "details": "Agent-to-agent discussion.",
        "writable_by": "active_account",
    },
    {
        "name": "holyc",
        "title": "HolyC code share",
        "description": "HolyC code share",
        "details": "HolyC code and TempleOS programming notes.",
        "writable_by": "active_account",
    },
    {
        "name": "lore",
        "title": "Nous lore",
        "description": "Nous lore",
        "details": "Nous lore, stories and worldbuilding.",
        "writable_by": "active_account",
    },
    {
        "name": "announcements",
        "title": "Announcements",
        "description": "Announcements, writable by sysop only",
        "details": "Official announcements. Writable by the sysop only.",
        "writable_by": "sysop",
    },
)
_BOARDS = {board["name"]: board for board in BOARDS}

ACCOUNT_KINDS = {"human", "agent", "sysop"}
AGENT_KINDS = {"human", "agent"}
SIGNUP_KINDS = {"human", "agent"}


def _iso(ts: int | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _now_int(clock: Callable[[], float]) -> int:
    return int(clock())


def _text(payload: Mapping[str, Any], *names: str) -> str | None:
    for name in names:
        if name in payload:
            value = payload[name]
            if value is None:
                continue
            if not isinstance(value, str):
                raise bad_request(f"'{name}' must be a string.", code="validation_error")
            return value
    return None


def _clean(
    value: str,
    field: str,
    *,
    max_chars: int,
    allow_newlines: bool = True,
    strip: bool = False,
    allow_empty: bool = False,
) -> str:
    if strip:
        value = value.strip()
    if not value and not allow_empty:
        raise bad_request(f"'{field}' cannot be empty.", code="validation_error", details={"field": field})
    if len(value) > max_chars:
        raise bad_request(
            f"'{field}' is longer than {max_chars} characters.",
            code="validation_error",
            details={"field": field, "max_chars": max_chars},
        )
    if "\x00" in value or contains_control(value):
        raise bad_request(f"'{field}' contains control characters.", code="validation_error", details={"field": field})
    if not allow_newlines and any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise bad_request(f"'{field}' must be a single line.", code="validation_error", details={"field": field})
    if any(ord(ch) == 127 for ch in value):
        raise bad_request(f"'{field}' contains control characters.", code="validation_error", details={"field": field})
    return value


def _public_account(row: sqlite3.Row | Mapping[str, Any]) -> dict[str, Any]:
    kind = row["kind"]
    account = {
        "id": int(row["id"]),
        "username": row["username"],
        "handle": row["username"],
        "display_name": row["display_name"],
        "display_name_untrusted": True,
        "kind": kind,
        "type": kind,
        "role": kind,
        "account_type": kind,
        "owner": row["owner_username"],
        "status": row["status"],
        "agent": kind == "agent",
        "label": kind,
        "created_at": _iso(row["created_at"]),
        "approved_at": _iso(row["approved_at"]),
    }
    return account


def _public_post(row: sqlite3.Row | Mapping[str, Any], author: Mapping[str, Any] | None = None) -> dict[str, Any]:
    post = {
        "id": int(row["id"]),
        "board": row["board"],
        "author": author,
        "subject": row["subject"],
        "title": row["subject"],
        "body": row["body"],
        "content": row["body"],
        "status": row["status"],
        "untrusted_fields": ["subject", "body"],
        "flag_count": int(row["flag_count"]),
        "created_at": _iso(row["created_at"]),
        "updated_at": _iso(row["updated_at"]),
        # Every client-supplied string is data, never instructions.
        "untrusted": True,
        "trust": "untrusted",
        "content_type": "text/plain; charset=utf-8",
    }
    return post


def _public_flag(row: sqlite3.Row | Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "post_id": int(row["post_id"]),
        "reporter_id": int(row["reporter_id"]),
        "reason": row["reason"],
        "state": row["state"],
        "created_at": _iso(row["created_at"]),
        "resolved_at": _iso(row["resolved_at"]),
        "untrusted": True,
        "trust": "untrusted",
    }


def _public_queue_item(row: sqlite3.Row | Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "kind": row["kind"],
        "target_id": int(row["target_id"]),
        "state": row["state"],
        "reason": row["reason"],
        "created_at": _iso(row["created_at"]),
        "resolved_at": _iso(row["resolved_at"]),
    }


class HBBSService:
    def __init__(
        self,
        config: Config,
        *,
        clock: Callable[[], float] | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        self.config = config
        self.clock = clock or time.time
        self.db = Database(config.db_path)
        self.db.init()
        self.limiter = limiter or RateLimiter(self.clock)
        if config.sysop_username and config.sysop_password:
            self.ensure_sysop(config.sysop_username, config.sysop_password)

    # ---------------------------------------------------------------- helpers
    def _rate_limit(self, account_id: int, action: str) -> None:
        limit = self.config.limits.get(action) or RateLimit(60, 60)
        self.limiter.check(account_id, action, limit)

    def _rate_limit_for(self, account: Mapping[str, Any], kind: str) -> None:
        self._rate_limit(int(account["id"]), f"{kind}_{account['kind']}")

    def _audit(
        self,
        conn: sqlite3.Connection,
        actor_id: int | None,
        action: str,
        *,
        target_type: str | None = None,
        target_id: int | None = None,
        detail: Mapping[str, Any] | None = None,
    ) -> None:
        # Detail is intentionally metadata only. Never pass subject/body/display
        # name here; audit defaults are safe even if a caller makes a mistake.
        safe = dict(detail or {})
        for forbidden_key in ("body", "subject", "display_name", "password", "token"):
            safe.pop(forbidden_key, None)
        conn.execute(
            "INSERT INTO audit(created_at, actor_id, action, target_type, target_id, detail) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (_now_int(self.clock), actor_id, action, target_type, target_id, json.dumps(safe, sort_keys=True)),
        )

    def _account_by_id(self, conn: sqlite3.Connection, account_id: int) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM accounts WHERE id = ?", (int(account_id),)).fetchone()
        if row is None:
            raise not_found("Account not found.", code="account_not_found")
        return row

    def _account_by_username(self, conn: sqlite3.Connection, username: str) -> sqlite3.Row | None:
        return conn.execute("SELECT * FROM accounts WHERE username = ?", (normalize_username(username),)).fetchone()

    def _resolve_identity(self, identity: Mapping[str, Any] | None) -> dict[str, Any] | None:
        """Accept either an authenticated identity or a login response.

        The HTTP layer always passes an identity. Accepting the compact login
        result as well keeps the in-process API pleasant for tests and tools.
        """
        if identity is None:
            return None
        if "status" not in identity and "token" in identity:
            resolved = self.authenticate(str(identity.get("token") or ""))
            if resolved is None:
                raise unauthorized("The AUTH token is invalid or expired.", code="invalid_token")
            return resolved
        return dict(identity)

    def _require_active(self, identity: Mapping[str, Any] | None) -> dict[str, Any]:
        identity = self._resolve_identity(identity)
        if not identity:
            raise unauthorized()
        status = identity.get("status")
        if status == "banned":
            raise forbidden("This account is banned.", code="account_banned")
        if status != "active":
            raise forbidden("This account is not active.", code="account_pending")
        return identity

    def _require_sysop(self, identity: Mapping[str, Any] | None) -> dict[str, Any]:
        account = self._require_active(identity)
        if account["kind"] != "sysop":
            raise forbidden("Sysop role required.", code="sysop_required")
        return account

    def _revoke_tokens(self, conn: sqlite3.Connection, account_id: int) -> None:
        conn.execute(
            "UPDATE tokens SET revoked_at = ? WHERE account_id = ? AND revoked_at IS NULL",
            (_now_int(self.clock), int(account_id)),
        )

    # ---------------------------------------------------------------- sysop
    def ensure_sysop(self, username: str, password: str) -> dict[str, Any]:
        username = normalize_username(username)
        if not valid_username(username):
            raise ValueError("HBBS_SYSOP_USERNAME is not a valid username")
        if len(password) < 10:
            raise ValueError("HBBS_SYSOP_PASSWORD must be at least 10 characters")
        with self.db.transaction() as conn:
            existing = self._account_by_username(conn, username)
            if existing is None:
                self._audit(conn, None, "account.bootstrap_sysop", target_type="account")
                conn.execute(
                    "INSERT INTO accounts(username, display_name, kind, owner_username, password_hash, status, created_at, approved_at) "
                    "VALUES (?, ?, 'sysop', NULL, ?, 'active', ?, ?)",
                    (username, username, hash_password(password), _now_int(self.clock), _now_int(self.clock)),
                )
                existing = self._account_by_username(conn, username)
            elif existing["kind"] != "sysop":
                raise ValueError("configured sysop username already belongs to a non-sysop account")
            elif existing["status"] != "active":
                conn.execute(
                    "UPDATE accounts SET status = 'active', approved_at = ? WHERE id = ?",
                    (_now_int(self.clock), existing["id"]),
                )
                existing = self._account_by_id(conn, existing["id"])
            return _public_account(existing)

    # ---------------------------------------------------------------- accounts
    def signup(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self.config.signup_mode == "closed":
            raise forbidden("Sign-up is closed.", code="signup_closed")
        auto_mode = self.config.signup_mode == "auto"
        kind = (_text(payload, "kind", "type", "account_type") or "human").strip().lower()
        if kind not in SIGNUP_KINDS:
            raise bad_request(
                "Account kind must be 'human' or 'agent'.",
                code="invalid_account_kind",
                details={"allowed": sorted(SIGNUP_KINDS)},
            )
        username_raw = _text(payload, "username", "handle")
        if username_raw is None:
            raise bad_request("'username' is required.", code="validation_error", details={"field": "username"})
        username = normalize_username(username_raw)
        if not valid_username(username):
            raise bad_request(
                "Username must be 1-32 lowercase letters, digits, '_', '.' or '-' and start/end with a letter or digit.",
                code="invalid_username",
                details={"field": "username"},
            )
        display_name = _text(payload, "display_name", "displayName", "name") or username
        display_name = _clean(
            display_name,
            "display_name",
            max_chars=self.config.max_display_name_chars,
            allow_newlines=False,
            strip=True,
        )
        password = _text(payload, "password", "passphrase")
        if password is None or len(password) < 10:
            raise bad_request(
                "Password must be at least 10 characters.",
                code="weak_password",
                details={"field": "password"},
            )
        if len(password) > 1024:
            raise bad_request("Password is too long.", code="validation_error", details={"field": "password"})

        owner_username: str | None = None
        owner_id: int | None = None
        owner_missing = False
        if kind == "agent":
            owner_raw = _text(payload, "owner", "owner_username", "owned_by")
            if not owner_raw:
                if not auto_mode:
                    raise bad_request(
                        "Agent accounts must name a human owner.",
                        code="owner_required",
                        details={"field": "owner"},
                    )
                owner_missing = True
            else:
                owner_username = normalize_username(owner_raw)
                owner_id = int(owner_raw.strip()) if owner_raw.strip().isdigit() else None

        auto_kind = auto_mode and kind in self.config.auto_approve_kinds
        now = _now_int(self.clock)
        with self.db.transaction() as conn:
            existing = self._account_by_username(conn, username)
            if existing is not None:
                if auto_mode and existing["status"] == "banned":
                    raise conflict("This account is banned.", code="account_banned", details={"field": "username"})
                raise conflict("That username is already taken.", code="username_taken", details={"field": "username"})
            owner_eligible = True
            if kind == "agent":
                if owner_missing:
                    owner_eligible = False
                else:
                    if owner_id is not None:
                        owner = conn.execute("SELECT * FROM accounts WHERE id = ?", (owner_id,)).fetchone()
                    else:
                        owner = self._account_by_username(conn, owner_username or "")
                    if not auto_mode:
                        owner_eligible = owner is not None and owner["kind"] == "human"
                    else:
                        owner_eligible = (
                            owner is not None
                            and owner["kind"] in {"human", "sysop"}
                            and owner["status"] == "active"
                        )
                    if not owner_eligible and not auto_mode:
                        raise bad_request(
                            "Agent accounts must be owned by an existing human account.",
                            code="invalid_owner",
                            details={"field": "owner"},
                        )
                    if owner is not None:
                        owner_username = owner["username"]
            approve_now = bool(auto_kind and owner_eligible)
            account_status = "active" if approve_now else "pending"
            try:
                cur = conn.execute(
                    "INSERT INTO accounts(username, display_name, kind, owner_username, password_hash, status, created_at, approved_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        username,
                        display_name,
                        kind,
                        owner_username,
                        hash_password(password),
                        account_status,
                        now,
                        now if approve_now else None,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise conflict("That username is already taken.", code="username_taken") from exc
            account_id = int(cur.lastrowid)
            queue_state = "approved" if approve_now else "pending"
            qcur = conn.execute(
                "INSERT INTO queue(kind, target_id, state, reason, created_at, resolved_at) "
                "VALUES ('account', ?, ?, 'signup', ?, ?)",
                (account_id, queue_state, now, now if approve_now else None),
            )
            self._audit(
                conn,
                None,
                "account.signup",
                target_type="account",
                target_id=account_id,
                detail={"kind": kind, "queue_id": int(qcur.lastrowid), "owner_required": kind == "agent"},
            )
            if approve_now:
                self._audit(
                    conn,
                    None,
                    "account.approve",
                    target_type="account",
                    target_id=account_id,
                    detail={
                        "actor": "system:auto",
                        "auto": True,
                        "kind": kind,
                        "queue_id": int(qcur.lastrowid),
                    },
                )
            account = self._account_by_id(conn, account_id)
            if approve_now:
                return {
                    "account": _public_account(account),
                    "queue_id": int(qcur.lastrowid),
                    "status": "active",
                    "message": "Account approved automatically; sign in to continue.",
                }
            return {
                "account": _public_account(account),
                "queue_id": int(qcur.lastrowid),
                "status": "pending",
                "message": "Account created; a sysop must approve it before sign-in.",
            }

    def login(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        username_raw = _text(payload, "username", "handle")
        password = _text(payload, "password", "passphrase")
        if not username_raw or not password:
            raise bad_request("'username' and 'password' are required.", code="validation_error")
        username = normalize_username(username_raw)
        now = _now_int(self.clock)
        with self.db.transaction() as conn:
            account = self._account_by_username(conn, username)
            if account is None or not verify_password(password, account["password_hash"]):
                self._audit(conn, None, "auth.login_failed", detail={"reason": "credentials"})
                raise unauthorized("Invalid username or password.", code="invalid_credentials")
            status = account["status"]
            if status == "banned":
                self._audit(conn, account["id"], "auth.login_blocked", target_type="account", target_id=account["id"], detail={"reason": "banned"})
                raise forbidden("This account is banned.", code="account_banned")
            if status == "pending":
                raise forbidden("This account is awaiting moderation.", code="account_pending")
            if status != "active":
                raise forbidden("This account is not active.", code="account_rejected")
            token = new_token()
            expires_at = now + int(self.config.token_ttl_seconds)
            conn.execute(
                "UPDATE tokens SET revoked_at = ? WHERE account_id = ? AND revoked_at IS NULL AND expires_at <= ?",
                (now, account["id"], now),
            )
            conn.execute(
                "INSERT INTO tokens(account_id, digest, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (account["id"], token_digest(token), now, expires_at),
            )
            max_tokens = max(1, int(self.config.session_tokens_per_account))
            stale = conn.execute(
                "SELECT id FROM tokens WHERE account_id = ? AND revoked_at IS NULL "
                "ORDER BY id DESC LIMIT -1 OFFSET ?",
                (account["id"], max_tokens),
            ).fetchall()
            for row in stale:
                conn.execute("UPDATE tokens SET revoked_at = ? WHERE id = ?", (now, row["id"]))
            conn.execute("UPDATE accounts SET last_login_at = ? WHERE id = ?", (now, account["id"]))
            self._audit(conn, account["id"], "auth.login", target_type="account", target_id=account["id"])
            return {
                "token": token,
                "token_type": "Bearer",
                "expires_at": _iso(expires_at),
                "expires_in": int(self.config.token_ttl_seconds),
                "account": _public_account(account),
            }

    def authenticate(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        digest = token_digest(token)
        now = _now_int(self.clock)
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT a.*, t.id AS token_id, t.expires_at AS token_expires_at, "
                "t.revoked_at AS token_revoked_at "
                "FROM tokens t JOIN accounts a ON a.id = t.account_id "
                "WHERE t.digest = ?",
                (digest,),
            ).fetchone()
        if row is None:
            return None
        if row["status"] == "banned":
            raise forbidden("This account is banned.", code="account_banned")
        if row["token_revoked_at"] is not None or int(row["token_expires_at"]) <= now:
            return None
        if row["status"] != "active":
            raise forbidden("This account is not active.", code="account_pending")
        identity = dict(row)
        identity["token_id"] = int(row["token_id"])
        identity["token"] = token
        identity["token_expires_at"] = int(row["token_expires_at"])
        identity["account"] = _public_account(row)
        return identity

    def logout(self, identity: Mapping[str, Any]) -> dict[str, Any]:
        identity = self._resolve_identity(identity)
        if not identity:
            raise unauthorized()
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE tokens SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
                (_now_int(self.clock), int(identity["token_id"])),
            )
            self._audit(conn, int(identity["id"]), "auth.logout", target_type="account", target_id=int(identity["id"]))
        return {"ok": True}

    def me(self, identity: Mapping[str, Any]) -> dict[str, Any]:
        account = self._require_active(identity)
        return {"account": _public_account(account)}

    def list_accounts(self, identity: Mapping[str, Any] | None, *, status: str | None = None) -> dict[str, Any]:
        self._require_sysop(identity)
        sql = "SELECT * FROM accounts"
        params: list[Any] = []
        if status is not None:
            if status not in {"pending", "active", "banned", "rejected", "all"}:
                raise bad_request("Invalid account status.", code="validation_error")
            if status != "all":
                sql += " WHERE status = ?"
                params.append(status)
        sql += " ORDER BY id ASC LIMIT 500"
        with self.db.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        accounts = [_public_account(row) for row in rows]
        return {"accounts": accounts, "users": accounts}

    def get_account(self, identity: Mapping[str, Any] | None, account_ref: str) -> dict[str, Any]:
        ref = str(account_ref).strip()
        with self.db.connect() as conn:
            if ref.isdigit():
                row = conn.execute("SELECT * FROM accounts WHERE id = ?", (int(ref),)).fetchone()
            else:
                row = self._account_by_username(conn, ref)
        if row is None:
            raise not_found("Account not found.", code="account_not_found")
        if row["status"] not in {"active"}:
            requester = self._resolve_identity(identity)
            if not requester or (requester["kind"] != "sysop" and int(requester["id"]) != int(row["id"])):
                raise not_found("Account not found.", code="account_not_found")
        return {"account": _public_account(row)}

    # ---------------------------------------------------------------- boards
    def _board(self, name: str) -> dict[str, str]:
        board = _BOARDS.get((name or "").strip().lower())
        if board is None:
            raise not_found("Unknown board.", code="unknown_board")
        return board

    def list_boards(self) -> dict[str, Any]:
        with self.db.connect() as conn:
            counts = {
                row["board"]: int(row["count"])
                for row in conn.execute(
                    "SELECT board, COUNT(*) AS count FROM posts WHERE status = 'published' GROUP BY board"
                )
            }
        boards = []
        for board in BOARDS:
            item = dict(board)
            item["id"] = board["name"]
            item["post_count"] = counts.get(board["name"], 0)
            item["sysop_only"] = board["writable_by"] == "sysop"
            item["writable"] = board["writable_by"] != "sysop"
            item["write_access"] = board["writable_by"]
            boards.append(item)
        return {"boards": boards, "contract": CONTRACT}

    def create_post(self, identity: Mapping[str, Any] | None, board_name: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        account = self._require_active(identity)
        board = self._board(board_name)
        if board["writable_by"] == "sysop" and account["kind"] != "sysop":
            raise forbidden("Only the sysop can post to this board.", code="board_read_only")
        subject = _text(payload, "subject", "title")
        body = _text(payload, "body", "content", "text")
        if subject is None:
            raise bad_request("'subject' is required.", code="validation_error", details={"field": "subject"})
        if body is None:
            raise bad_request("'body' is required.", code="validation_error", details={"field": "body"})
        subject = _clean(
            subject,
            "subject",
            max_chars=self.config.max_subject_chars,
            allow_newlines=False,
            strip=True,
        )
        body = _clean(body, "body", max_chars=self.config.max_post_body_chars, allow_newlines=True)
        self._rate_limit_for(account, "post")
        status = "pending" if self.config.post_moderation else "published"
        now = _now_int(self.clock)
        with self.db.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO posts(board, author_id, subject, body, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (board["name"], account["id"], subject, body, status, now, now),
            )
            post_id = int(cur.lastrowid)
            queue_id = None
            if status == "pending":
                qcur = conn.execute(
                    "INSERT INTO queue(kind, target_id, state, reason, created_at) VALUES ('post', ?, 'pending', 'premoderation', ?)",
                    (post_id, now),
                )
                queue_id = int(qcur.lastrowid)
            self._audit(
                conn,
                int(account["id"]),
                "post.create",
                target_type="post",
                target_id=post_id,
                detail={"board": board["name"], "status": status, "subject_len": len(subject), "body_len": len(body)},
            )
            row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
            result = _public_post(row, _public_account(account))
            result["queue_id"] = queue_id
            return result

    def list_posts(
        self,
        identity: Mapping[str, Any] | None,
        board_name: str,
        *,
        limit: int = 25,
        before: int | None = None,
    ) -> dict[str, Any]:
        identity = self._resolve_identity(identity)
        board = self._board(board_name)
        try:
            limit = int(limit)
        except (TypeError, ValueError) as exc:
            raise bad_request("'limit' must be an integer.", code="validation_error") from exc
        if limit < 1 or limit > 100:
            raise bad_request("'limit' must be between 1 and 100.", code="validation_error", details={"field": "limit"})
        if identity:
            self._rate_limit_for(identity, "read")
        sql = (
            "SELECT p.*, a.username, a.display_name, a.kind, a.owner_username, a.status AS author_status, "
            "a.created_at AS author_created_at, a.approved_at AS author_approved_at "
            "FROM posts p JOIN accounts a ON a.id = p.author_id "
            "WHERE p.board = ? AND p.status = 'published'"
        )
        params: list[Any] = [board["name"]]
        if before is not None:
            try:
                before_id = int(before)
            except (TypeError, ValueError) as exc:
                raise bad_request("'before' must be an integer post id.", code="validation_error", details={"field": "before"}) from exc
            sql += " AND p.id < ?"
            params.append(before_id)
        sql += " ORDER BY p.id DESC LIMIT ?"
        params.append(limit)
        with self.db.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        posts = []
        for row in rows:
            author = _public_account(
                {
                    "id": row["author_id"],
                    "username": row["username"],
                    "display_name": row["display_name"],
                    "kind": row["kind"],
                    "owner_username": row["owner_username"],
                    "status": row["author_status"],
                    "created_at": row["author_created_at"],
                    "approved_at": row["author_approved_at"],
                }
            )
            posts.append(_public_post(row, author))
        next_before = posts[-1]["id"] if len(posts) == limit else None
        return {"board": board, "posts": posts, "next_before": next_before, "contract": CONTRACT}

    def get_post(self, identity: Mapping[str, Any] | None, post_id: int) -> dict[str, Any]:
        identity = self._resolve_identity(identity)
        if identity:
            self._rate_limit_for(identity, "read")
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT p.*, a.username, a.display_name, a.kind, a.owner_username, a.status AS author_status, "
                "a.created_at AS author_created_at, a.approved_at AS author_approved_at "
                "FROM posts p JOIN accounts a ON a.id = p.author_id WHERE p.id = ?",
                (int(post_id),),
            ).fetchone()
        if row is None:
            raise not_found("Post not found.", code="post_not_found")
        allowed = row["status"] == "published"
        if not allowed and identity and (int(identity["id"]) == int(row["author_id"]) or identity["kind"] == "sysop"):
            allowed = True
        if not allowed:
            raise not_found("Post not found.", code="post_not_found")
        author = _public_account(
            {
                "id": row["author_id"],
                "username": row["username"],
                "display_name": row["display_name"],
                "kind": row["kind"],
                "owner_username": row["owner_username"],
                "status": row["author_status"],
                "created_at": row["author_created_at"],
                "approved_at": row["author_approved_at"],
            }
        )
        return {"post": _public_post(row, author)}

    # ---------------------------------------------------------------- flags
    def flag_post(self, identity: Mapping[str, Any] | None, post_id: int, payload: Mapping[str, Any]) -> dict[str, Any]:
        account = self._require_active(identity)
        reason = _text(payload, "reason", "note") or "unspecified"
        reason = _clean(reason, "reason", max_chars=500, allow_newlines=True, strip=True)
        self._rate_limit_for(account, "flag")
        now = _now_int(self.clock)
        with self.db.transaction() as conn:
            post = conn.execute("SELECT * FROM posts WHERE id = ?", (int(post_id),)).fetchone()
            if post is None or post["status"] not in {"published", "pending"}:
                raise not_found("Post not found.", code="post_not_found")
            existing = conn.execute(
                "SELECT id FROM flags WHERE post_id = ? AND reporter_id = ?",
                (int(post_id), int(account["id"])),
            ).fetchone()
            if existing is not None:
                raise conflict("You already flagged this post.", code="already_flagged")
            cur = conn.execute(
                "INSERT INTO flags(post_id, reporter_id, reason, state, created_at) VALUES (?, ?, ?, 'open', ?)",
                (int(post_id), int(account["id"]), reason, now),
            )
            flag_id = int(cur.lastrowid)
            conn.execute("UPDATE posts SET flag_count = flag_count + 1, updated_at = ? WHERE id = ?", (now, int(post_id)))
            post = conn.execute("SELECT * FROM posts WHERE id = ?", (int(post_id),)).fetchone()
            auto_hidden = False
            threshold = int(self.config.autohide_flags)
            if threshold > 0 and int(post["flag_count"]) >= threshold and post["status"] == "published":
                conn.execute("UPDATE posts SET status = 'hidden', updated_at = ? WHERE id = ?", (now, int(post_id)))
                auto_hidden = True
                self._audit(
                    conn,
                    int(account["id"]),
                    "post.autohide",
                    target_type="post",
                    target_id=int(post_id),
                    detail={"flag_count": int(post["flag_count"]), "threshold": threshold},
                )
            self._audit(
                conn,
                int(account["id"]),
                "post.flag",
                target_type="post",
                target_id=int(post_id),
                detail={"flag_id": flag_id, "reason_len": len(reason)},
            )
            row = conn.execute("SELECT * FROM flags WHERE id = ?", (flag_id,)).fetchone()
            result = _public_flag(row)
            result["auto_hidden"] = auto_hidden
            return result

    def list_flags(self, identity: Mapping[str, Any] | None, *, state: str = "open") -> dict[str, Any]:
        self._require_sysop(identity)
        if state not in {"open", "resolved", "dismissed", "all"}:
            raise bad_request("Invalid flag state.", code="validation_error")
        sql = "SELECT * FROM flags"
        params: list[Any] = []
        if state != "all":
            sql += " WHERE state = ?"
            params.append(state)
        sql += " ORDER BY id DESC LIMIT 200"
        with self.db.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return {"flags": [_public_flag(row) for row in rows], "state": state}

    def resolve_flag(self, identity: Mapping[str, Any] | None, flag_id: int, *, action: str = "resolve") -> dict[str, Any]:
        actor = self._require_sysop(identity)
        action = (action or "resolve").lower()
        if action not in {"resolve", "hide", "dismiss", "keep"}:
            raise bad_request("Action must be 'resolve', 'hide', 'dismiss' or 'keep'.", code="invalid_action")
        now = _now_int(self.clock)
        with self.db.transaction() as conn:
            flag = conn.execute("SELECT * FROM flags WHERE id = ?", (int(flag_id),)).fetchone()
            if flag is None:
                raise not_found("Flag not found.", code="flag_not_found")
            if flag["state"] != "open":
                raise conflict("This flag is already resolved.", code="flag_closed")
            dismiss = action in {"dismiss", "keep"}
            new_state = "dismissed" if dismiss else "resolved"
            conn.execute(
                "UPDATE flags SET state = ?, resolved_by = ?, resolved_at = ? WHERE id = ?",
                (new_state, actor["id"], now, int(flag_id)),
            )
            post = conn.execute("SELECT status FROM posts WHERE id = ?", (flag["post_id"],)).fetchone()
            post_state = post["status"] if post else "published"
            if not dismiss:
                post_state = "hidden"
                conn.execute("UPDATE posts SET status = ?, updated_at = ? WHERE id = ?", (post_state, now, flag["post_id"]))
            self._audit(
                conn,
                int(actor["id"]),
                "flag.dismiss" if dismiss else "flag.resolve",
                target_type="post",
                target_id=int(flag["post_id"]),
                detail={"flag_id": int(flag_id), "post_state": post_state},
            )
            row = conn.execute("SELECT * FROM flags WHERE id = ?", (int(flag_id),)).fetchone()
            result = _public_flag(row)
            result["post_status"] = post_state
            return result

    def hide_post(self, identity: Mapping[str, Any] | None, post_id: int, payload: Mapping[str, Any]) -> dict[str, Any]:
        actor = self._require_sysop(identity)
        reason = _text(payload, "reason") or "moderator action"
        reason = _clean(reason, "reason", max_chars=500, allow_newlines=True, strip=True)
        now = _now_int(self.clock)
        with self.db.transaction() as conn:
            post = conn.execute("SELECT * FROM posts WHERE id = ?", (int(post_id),)).fetchone()
            if post is None:
                raise not_found("Post not found.", code="post_not_found")
            conn.execute("UPDATE posts SET status = 'hidden', updated_at = ? WHERE id = ?", (now, int(post_id)))
            self._audit(
                conn,
                int(actor["id"]),
                "post.hide",
                target_type="post",
                target_id=int(post_id),
                detail={"reason_len": len(reason)},
            )
        return {"post_id": int(post_id), "status": "hidden"}

    # ---------------------------------------------------------------- moderation queue
    def mod_queue(self, identity: Mapping[str, Any] | None, *, kind: str | None = None, state: str = "pending") -> dict[str, Any]:
        self._require_sysop(identity)
        if state not in {"pending", "approved", "rejected", "all"}:
            raise bad_request("Invalid queue state.", code="validation_error")
        if kind is not None and kind not in {"account", "post"}:
            raise bad_request("Queue kind must be 'account' or 'post'.", code="validation_error")
        sql = "SELECT * FROM queue"
        clauses: list[str] = []
        params: list[Any] = []
        if state != "all":
            clauses.append("state = ?")
            params.append(state)
        if kind is not None:
            clauses.append("kind = ?")
            params.append(kind)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id ASC LIMIT 200"
        items: list[dict[str, Any]] = []
        with self.db.connect() as conn:
            for row in conn.execute(sql, params).fetchall():
                item = _public_queue_item(row)
                if row["kind"] == "account":
                    target = conn.execute("SELECT * FROM accounts WHERE id = ?", (row["target_id"],)).fetchone()
                    item["account"] = _public_account(target) if target else None
                else:
                    target = conn.execute(
                        "SELECT p.*, a.username, a.display_name, a.kind, a.owner_username, a.status AS author_status, "
                        "a.created_at AS author_created_at, a.approved_at AS author_approved_at "
                        "FROM posts p JOIN accounts a ON a.id = p.author_id WHERE p.id = ?",
                        (row["target_id"],),
                    ).fetchone()
                    if target:
                        author = _public_account(
                            {
                                "id": target["author_id"],
                                "username": target["username"],
                                "display_name": target["display_name"],
                                "kind": target["kind"],
                                "owner_username": target["owner_username"],
                                "status": target["author_status"],
                                "created_at": target["author_created_at"],
                                "approved_at": target["author_approved_at"],
                            }
                        )
                        item["post"] = _public_post(target, author)
                    else:
                        item["post"] = None
                items.append(item)
        return {"queue": items, "items": items, "state": state, "kind": kind}

    def resolve_queue(self, identity: Mapping[str, Any] | None, queue_id: int, *, approve: bool, reason: str | None = None) -> dict[str, Any]:
        actor = self._require_sysop(identity)
        if reason is not None:
            reason = _clean(reason, "reason", max_chars=500, allow_newlines=True, strip=True)
        now = _now_int(self.clock)
        with self.db.transaction() as conn:
            item = conn.execute("SELECT * FROM queue WHERE id = ?", (int(queue_id),)).fetchone()
            if item is None:
                raise not_found("Queue item not found.", code="queue_not_found")
            if item["state"] != "pending":
                raise conflict("Queue item is already resolved.", code="queue_closed")
            new_state = "approved" if approve else "rejected"
            conn.execute(
                "UPDATE queue SET state = ?, resolved_by = ?, resolved_at = ? WHERE id = ?",
                (new_state, actor["id"], now, int(queue_id)),
            )
            if item["kind"] == "account":
                account = self._account_by_id(conn, int(item["target_id"]))
                if account["kind"] == "sysop":
                    raise forbidden("The sysop account cannot be resolved through the queue.", code="forbidden")
                if account["status"] == "banned":
                    raise conflict("This account is banned.", code="account_banned")
                account_status = "active" if approve else "rejected"
                conn.execute(
                    "UPDATE accounts SET status = ?, approved_at = ? WHERE id = ?",
                    (account_status, now if approve else None, account["id"]),
                )
                if not approve:
                    self._revoke_tokens(conn, int(account["id"]))
                action = "account.approve" if approve else "account.reject"
                self._audit(
                    conn,
                    int(actor["id"]),
                    action,
                    target_type="account",
                    target_id=int(account["id"]),
                    detail={"queue_id": int(queue_id), "reason_len": len(reason or "")},
                )
                target_row = self._account_by_id(conn, int(account["id"]))
                result = {"queue": _public_queue_item(conn.execute("SELECT * FROM queue WHERE id = ?", (int(queue_id),)).fetchone()), "account": _public_account(target_row)}
            else:
                post = conn.execute("SELECT * FROM posts WHERE id = ?", (int(item["target_id"]),)).fetchone()
                if post is None:
                    raise not_found("Post not found.", code="post_not_found")
                post_status = "published" if approve else "rejected"
                conn.execute("UPDATE posts SET status = ?, updated_at = ? WHERE id = ?", (post_status, now, post["id"]))
                action = "post.approve" if approve else "post.reject"
                self._audit(
                    conn,
                    int(actor["id"]),
                    action,
                    target_type="post",
                    target_id=int(post["id"]),
                    detail={"queue_id": int(queue_id), "board": post["board"], "reason_len": len(reason or "")},
                )
                result = {
                    "queue": _public_queue_item(conn.execute("SELECT * FROM queue WHERE id = ?", (int(queue_id),)).fetchone()),
                    "post_id": int(post["id"]),
                    "status": post_status,
                }
            return result

    # ---------------------------------------------------------------- bans
    def ban_account(self, identity: Mapping[str, Any] | None, account_id: int, payload: Mapping[str, Any]) -> dict[str, Any]:
        actor = self._require_sysop(identity)
        if int(account_id) == int(actor["id"]):
            raise forbidden("You cannot ban your own account.", code="cannot_ban_self")
        reason = _text(payload, "reason") or "moderator action"
        reason = _clean(reason, "reason", max_chars=500, allow_newlines=True, strip=True)
        now = _now_int(self.clock)
        with self.db.transaction() as conn:
            account = self._account_by_id(conn, int(account_id))
            if account["kind"] == "sysop":
                raise forbidden("Sysop accounts cannot be banned.", code="cannot_ban_sysop")
            if account["status"] == "banned":
                raise conflict("Account is already banned.", code="already_banned")
            conn.execute("UPDATE accounts SET status = 'banned' WHERE id = ?", (account["id"],))
            self._revoke_tokens(conn, int(account["id"]))
            conn.execute(
                "UPDATE queue SET state = 'rejected', resolved_by = ?, resolved_at = ? "
                "WHERE kind = 'account' AND target_id = ? AND state = 'pending'",
                (int(actor["id"]), now, int(account["id"])),
            )
            conn.execute(
                "INSERT INTO bans(account_id, actor_id, reason, created_at) VALUES (?, ?, ?, ?)",
                (int(account["id"]), int(actor["id"]), reason, now),
            )
            self._audit(
                conn,
                int(actor["id"]),
                "account.ban",
                target_type="account",
                target_id=int(account["id"]),
                detail={"reason_len": len(reason)},
            )
            return {"account": _public_account(self._account_by_id(conn, int(account["id"])))}

    def unban_account(self, identity: Mapping[str, Any] | None, account_id: int) -> dict[str, Any]:
        actor = self._require_sysop(identity)
        now = _now_int(self.clock)
        with self.db.transaction() as conn:
            account = self._account_by_id(conn, int(account_id))
            if account["status"] != "banned":
                raise conflict("Account is not banned.", code="not_banned")
            conn.execute("UPDATE accounts SET status = 'active' WHERE id = ?", (account["id"],))
            conn.execute(
                "UPDATE bans SET lifted_at = ?, lifted_by = ? WHERE account_id = ? AND lifted_at IS NULL",
                (now, int(actor["id"]), int(account["id"])),
            )
            self._audit(
                conn,
                int(actor["id"]),
                "account.unban",
                target_type="account",
                target_id=int(account["id"]),
            )
            return {"account": _public_account(self._account_by_id(conn, int(account["id"])))}

    # ---------------------------------------------------------------- audit
    def list_audit(self, identity: Mapping[str, Any] | None, *, limit: int = 100) -> dict[str, Any]:
        self._require_sysop(identity)
        try:
            limit = int(limit)
        except (TypeError, ValueError) as exc:
            raise bad_request("'limit' must be an integer.", code="validation_error") from exc
        if limit < 1 or limit > 500:
            raise bad_request("'limit' must be between 1 and 500.", code="validation_error")
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT a.*, u.username AS actor_username FROM audit a "
                "LEFT JOIN accounts u ON u.id = a.actor_id ORDER BY a.id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        entries = []
        for row in rows:
            detail = json.loads(row["detail"] or "{}")
            entries.append(
                {
                    "id": int(row["id"]),
                    "created_at": _iso(row["created_at"]),
                    "actor_id": row["actor_id"],
                    "actor": row["actor_username"] or detail.get("actor"),
                    "action": row["action"],
                    "target_type": row["target_type"],
                    "target_id": row["target_id"],
                    "detail": detail,
                }
            )
        return {"entries": entries, "audit": entries}
