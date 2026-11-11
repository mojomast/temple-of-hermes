"""SQLite persistence for HBBS/1.

The schema is intentionally small and migration-friendly. Every value that a
client supplies is stored as data and passed through SQL parameters; no user
text is ever interpolated into SQL.
"""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 1

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('human', 'agent', 'sysop')),
    owner_username TEXT,
    password_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'active', 'banned', 'rejected')),
    created_at INTEGER NOT NULL,
    approved_at INTEGER,
    last_login_at INTEGER
);

CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    digest TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    revoked_at INTEGER
);
CREATE INDEX IF NOT EXISTS tokens_account_idx ON tokens(account_id);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    board TEXT NOT NULL,
    author_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('published', 'pending', 'hidden', 'rejected')),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    flag_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS posts_board_idx ON posts(board, status, id DESC);

CREATE TABLE IF NOT EXISTS flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    reporter_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('open', 'resolved', 'dismissed')),
    created_at INTEGER NOT NULL,
    resolved_by INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    resolved_at INTEGER,
    UNIQUE (post_id, reporter_id)
);
CREATE INDEX IF NOT EXISTS flags_state_idx ON flags(state, id);

CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('account', 'post')),
    target_id INTEGER NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('pending', 'approved', 'rejected')),
    reason TEXT,
    created_at INTEGER NOT NULL,
    resolved_by INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    resolved_at INTEGER,
    UNIQUE (kind, target_id)
);
CREATE INDEX IF NOT EXISTS queue_state_idx ON queue(state, id);

CREATE TABLE IF NOT EXISTS bans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    actor_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    reason TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    lifted_at INTEGER,
    lifted_by INTEGER REFERENCES accounts(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS bans_account_idx ON bans(account_id, lifted_at);

CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at INTEGER NOT NULL,
    actor_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id INTEGER,
    detail TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS audit_created_idx ON audit(id DESC);
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self._memory = str(path) == ":memory:"
        if self._memory:
            # A shared-cache in-memory database plus an anchor connection lets
            # each operation open and close its own connection safely.
            self.path = f"file:hbbs_{uuid.uuid4().hex}?mode=memory&cache=shared"
            self._anchor = sqlite3.connect(self.path, uri=True, timeout=10, isolation_level=None)
            self._anchor.row_factory = sqlite3.Row
        else:
            self.path = str(path)
            self._anchor = None
            parent = Path(self.path).expanduser().parent
            parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, uri=self._memory, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            if not self._memory:
                conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 10000")
            yield conn
        finally:
            conn.close()

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(_SCHEMA)
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")
