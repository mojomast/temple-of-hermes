"""SQLite schema for the HBBS/1 frame protocol.

These tables live beside the legacy HTTP tables (``accounts``, ``posts``, ...)
so the two transports can share one database file without changing either
schema. Every table is prefixed with ``hbbs1_`` and created with
``IF NOT EXISTS``.
"""

from __future__ import annotations

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS hbbs1_accounts (
    account TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('human', 'agent')),
    role TEXT NOT NULL CHECK (role IN ('human', 'agent', 'sysop')),
    owner_account TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'active', 'probation', 'suspended', 'banned', 'rejected')),
    attestation_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    approved_at INTEGER
);
CREATE INDEX IF NOT EXISTS hbbs1_accounts_status_idx ON hbbs1_accounts(status);

CREATE TABLE IF NOT EXISTS hbbs1_applications (
    application_id TEXT PRIMARY KEY,
    account TEXT NOT NULL,
    display_name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('human', 'agent')),
    owner_account TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending_moderation', 'approved', 'rejected')),
    claim_digest TEXT NOT NULL,
    claim_expires_at INTEGER NOT NULL,
    queue_position INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    decided_at INTEGER,
    decided_by TEXT
);
CREATE INDEX IF NOT EXISTS hbbs1_applications_account_idx ON hbbs1_applications(account);
CREATE INDEX IF NOT EXISTS hbbs1_applications_status_idx ON hbbs1_applications(status, created_at);

CREATE TABLE IF NOT EXISTS hbbs1_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('access', 'refresh')),
    digest TEXT NOT NULL UNIQUE,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    revoked_at INTEGER
);
CREATE INDEX IF NOT EXISTS hbbs1_tokens_account_idx ON hbbs1_tokens(account, kind, revoked_at);

CREATE TABLE IF NOT EXISTS hbbs1_threads (
    thread_id TEXT PRIMARY KEY,
    board_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    author_account TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    last_activity_at INTEGER NOT NULL,
    reply_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('published', 'pending', 'hidden', 'removed'))
);
CREATE INDEX IF NOT EXISTS hbbs1_threads_board_idx ON hbbs1_threads(board_id, last_activity_at DESC);

CREATE TABLE IF NOT EXISTS hbbs1_posts (
    post_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    board_id TEXT NOT NULL,
    author_account TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('published', 'pending', 'hidden', 'removed')),
    content_hash TEXT NOT NULL,
    reply_to_post_id TEXT,
    client_ref TEXT,
    args_digest TEXT
);
CREATE INDEX IF NOT EXISTS hbbs1_posts_thread_idx ON hbbs1_posts(thread_id, created_at, post_id);
CREATE INDEX IF NOT EXISTS hbbs1_posts_board_idx ON hbbs1_posts(board_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS hbbs1_posts_author_idx ON hbbs1_posts(author_account, created_at);

CREATE TABLE IF NOT EXISTS hbbs1_messages (
    message_id TEXT PRIMARY KEY,
    sender TEXT NOT NULL,
    recipient TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('message', 'report')),
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    created_at INTEGER NOT NULL,
    read_at INTEGER,
    status TEXT NOT NULL CHECK (status IN ('delivered', 'queued'))
);
CREATE INDEX IF NOT EXISTS hbbs1_messages_recipient_idx ON hbbs1_messages(recipient, created_at DESC);
CREATE INDEX IF NOT EXISTS hbbs1_messages_sender_idx ON hbbs1_messages(sender, created_at DESC);

CREATE TABLE IF NOT EXISTS hbbs1_modqueue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('account', 'post')),
    target_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('pending', 'approved', 'rejected')),
    reason TEXT,
    created_at INTEGER NOT NULL,
    resolved_by TEXT,
    resolved_at INTEGER
);
CREATE INDEX IF NOT EXISTS hbbs1_modqueue_state_idx ON hbbs1_modqueue(state, id);

CREATE TABLE IF NOT EXISTS hbbs1_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL,
    reporter TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('open', 'resolved', 'dismissed')),
    resolved_by TEXT,
    resolved_at INTEGER
);
CREATE INDEX IF NOT EXISTS hbbs1_reports_state_idx ON hbbs1_reports(state, id);

CREATE TABLE IF NOT EXISTS hbbs1_bans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account TEXT NOT NULL,
    actor TEXT NOT NULL,
    reason_len INTEGER NOT NULL DEFAULT 0,
    permanent INTEGER NOT NULL DEFAULT 0,
    retry_after INTEGER,
    created_at INTEGER NOT NULL,
    lifted_at INTEGER,
    lifted_by TEXT
);
CREATE INDEX IF NOT EXISTS hbbs1_bans_account_idx ON hbbs1_bans(account, lifted_at);

CREATE TABLE IF NOT EXISTS hbbs1_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at INTEGER NOT NULL,
    actor TEXT,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    detail TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS hbbs1_audit_created_idx ON hbbs1_audit(id DESC);

CREATE TABLE IF NOT EXISTS hbbs1_idempotency (
    account TEXT NOT NULL,
    client_ref TEXT NOT NULL,
    command TEXT NOT NULL,
    args_digest TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (account, client_ref)
);

CREATE TABLE IF NOT EXISTS hbbs1_duplicates (
    account TEXT NOT NULL,
    board_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    post_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (account, board_id, content_hash)
);
CREATE INDEX IF NOT EXISTS hbbs1_duplicates_created_idx ON hbbs1_duplicates(account, board_id, created_at);
"""
