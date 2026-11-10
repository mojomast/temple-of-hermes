from __future__ import annotations

import http.client
import json
from dataclasses import replace

import pytest

from hbbs.http import start_background
from hbbs.service import HBBSService

from conftest import SYSOP, SYSOP_PASSWORD, make_config


def request(port: int, method: str, path: str, body=None, token: str | None = None,
            headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], dict]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    request_headers = dict(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    try:
        conn.request(method, path, body=data, headers=request_headers)
        response = conn.getresponse()
        raw = response.read()
        parsed = json.loads(raw.decode("utf-8")) if raw else {}
        return response.status, {key.lower(): value for key, value in response.getheaders()}, parsed
    finally:
        conn.close()


@pytest.fixture
def live(tmp_path, clock):
    config = replace(make_config(tmp_path), bind_port=0)
    service = HBBSService(config, clock=clock)
    server, thread = start_background(config, service)
    try:
        yield server.server_address[1], service
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def approve_account(service: HBBSService, username: str) -> None:
    sysop = service.login({"username": SYSOP, "password": SYSOP_PASSWORD})
    item = next(
        item for item in service.mod_queue(sysop, kind="account")["items"]
        if item["account"] and item["account"]["username"] == username
    )
    service.resolve_queue(sysop, item["id"], approve=True)


def test_health_boards_and_security_headers(live):
    port, _ = live
    status, headers, body = request(port, "GET", "/hbbs/v1/healthz")
    assert status == 200
    assert body["ok"] is True
    assert body["contract"] == "HBBS/1"
    assert body["status"] == "ok"
    assert headers["x-hbbs-contract"] == "HBBS/1"
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["cache-control"] == "no-store"

    status, _, body = request(port, "GET", "/v1/boards")
    assert status == 200
    assert [board["name"] for board in body["boards"]] == ["general", "agents", "holyc", "lore", "announcements"]

    status, _, body = request(port, "GET", "/boards")
    assert status == 200
    assert body["contract"] == "HBBS/1"


def test_http_signup_login_post_read(live):
    port, service = live
    status, _, body = request(port, "POST", "/hbbs/v1/accounts", {
        "username": "alice", "password": "a sufficiently long password", "display_name": "Alice"
    })
    assert status == 201
    assert body["ok"] is True
    assert body["account"]["status"] == "pending"

    status, _, body = request(port, "POST", "/v1/auth/login", {"username": "alice", "password": "a sufficiently long password"})
    assert status == 403
    assert body["code"] == "account_pending"

    approve_account(service, "alice")
    status, _, body = request(port, "POST", "/v1/auth/login", {"username": "alice", "password": "a sufficiently long password"})
    assert status == 200
    assert body["ok"] is True
    assert body["token_type"] == "Bearer"
    token = body["token"]

    status, _, body = request(port, "GET", "/v1/auth/me", token=token)
    assert status == 200
    assert body["account"]["username"] == "alice"

    status, _, body = request(port, "POST", "/v1/boards/general/posts", {
        "subject": "Hello from HTTP", "body": "line one\nline two"
    }, token=token)
    assert status == 201
    assert body["post"]["body"] == "line one\nline two"
    post_id = body["post"]["id"]

    status, _, body = request(port, "GET", "/v1/boards/general/posts")
    assert status == 200
    assert body["posts"][0]["id"] == post_id

    status, _, body = request(port, "GET", f"/v1/posts/{post_id}")
    assert status == 200
    assert body["post"]["untrusted"] is True

    status, _, body = request(port, "POST", f"/v1/posts/{post_id}/flags", {"reason": "test"}, token=token)
    assert status == 201
    assert body["flag"]["state"] == "open"

    status, _, body = request(port, "DELETE", "/v1/auth/session", token=token)
    assert status == 200
    status, _, body = request(port, "GET", "/v1/auth/me", token=token)
    assert status == 401
    assert body["code"] == "unauthorized"


def test_http_errors_are_structured_and_do_not_leak(live):
    port, _ = live
    status, _, body = request(port, "POST", "/v1/boards/general/posts", {"subject": "x", "body": "y"})
    assert status == 401
    assert body["ok"] is False
    assert body["code"] == "unauthorized"
    assert "Traceback" not in json.dumps(body)

    status, _, body = request(port, "GET", "/v1/boards/does-not-exist/posts")
    assert status == 404
    assert body["ok"] is False
    assert body["code"] == "unknown_board"

    status, _, body = request(port, "POST", "/v1/accounts", "not-a-json-object", headers={"Content-Type": "text/plain"})
    assert status == 415
    assert body["code"] == "unsupported_media_type"

    status, _, body = request(port, "GET", "/v1/no-such-route")
    assert status == 404
    assert body["code"] == "not_found"


def test_http_head_has_no_body(live):
    port, _ = live
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request("HEAD", "/hbbs/v1/healthz")
        response = conn.getresponse()
        assert response.status == 200
        assert response.read() == b""
    finally:
        conn.close()


def test_http_body_limit(tmp_path, clock):
    config = replace(make_config(tmp_path), bind_port=0, max_body_bytes=128)
    service = HBBSService(config, clock=clock)
    server, thread = start_background(config, service)
    port = server.server_address[1]
    try:
        status, _, body = request(port, "POST", "/v1/accounts", {"username": "alice", "password": "x" * 500})
        assert status == 413
        assert body["code"] == "payload_too_large"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_rate_limit_sets_retry_after(tmp_path, clock):
    from hbbs.config import RateLimit

    limits = {
        "post_human": RateLimit(1, 600),
        "post_agent": RateLimit(1, 600),
        "post_sysop": RateLimit(100, 600),
        "read_human": RateLimit(500, 60),
        "read_agent": RateLimit(500, 60),
        "flag_human": RateLimit(20, 3600),
        "flag_agent": RateLimit(20, 3600),
    }
    config = replace(make_config(tmp_path, limits=limits), bind_port=0)
    service = HBBSService(config, clock=clock)
    server, thread = start_background(config, service)
    port = server.server_address[1]
    try:
        request(port, "POST", "/v1/accounts", {"username": "alice", "password": "a sufficiently long password"})
        approve_account(service, "alice")
        status, _, body = request(port, "POST", "/v1/auth/login", {"username": "alice", "password": "a sufficiently long password"})
        token = body["token"]
        status, _, _ = request(port, "POST", "/v1/boards/general/posts", {"subject": "one", "body": "x"}, token=token)
        assert status == 201
        status, headers, body = request(port, "POST", "/v1/boards/general/posts", {"subject": "two", "body": "x"}, token=token)
        assert status == 429
        assert body["code"] == "rate_limited"
        assert int(headers["retry-after"]) >= 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
