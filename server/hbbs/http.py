"""Minimal HTTP transport for the HBBS/1 JSON API.

Only the Python standard library is used. The canonical prefix is
``/hbbs/v1``; several harmless aliases are accepted so small clients can use
``/v1`` or a bare path. TLS is configured from ``Config`` (and therefore from
the environment), never from a hostname baked into code.
"""

from __future__ import annotations

import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping
from urllib.parse import parse_qs, unquote, urlsplit

from .config import Config
from .errors import HBBSError, bad_request, not_found, too_large, unauthorized
from .service import CONTRACT, HBBSService


def envelope(payload: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "ok": True,
        "error": None,
        "code": None,
        "data": payload,
        "contract": CONTRACT,
    }
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if key not in body:
                body[key] = value
    elif isinstance(payload, list):
        body["items"] = payload
    return body


def _resource(name: str, value: Mapping[str, Any]) -> dict[str, Any]:
    """Return a payload with both a named resource and flattened top-level keys."""
    payload: dict[str, Any] = {name: value}
    for key, item in value.items():
        if key not in payload:
            payload[key] = item
    return payload


def _segments(path: str) -> list[str]:
    parts = [unquote(part) for part in path.split("/") if part]
    prefixes = {"api", "hbbs", "bbs", "v1", "1"}
    while parts and parts[0].lower() in prefixes:
        parts = parts[1:]
    return [part.lower() if index < 2 else part for index, part in enumerate(parts)]


class HBBSRequestHandler(BaseHTTPRequestHandler):
    server_version = "HBBS/1"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------------ plumbing
    def version_string(self) -> str:
        return self.server_version

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Never log paths, query strings, headers or bodies by default.
        return

    @property
    def service(self) -> HBBSService:
        return self.server.service  # type: ignore[attr-defined]

    def _send(self, status: int, payload: Mapping[str, Any], extra_headers: Mapping[str, str] | None = None) -> None:
        raw = b"" if status in {204, 304} else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-HBBS-Contract", CONTRACT)
        self.send_header("X-HBBS-Version", "1")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD" and raw:
            self.wfile.write(raw)

    def _error(self, exc: HBBSError) -> None:
        headers: dict[str, str] = {}
        retry = exc.details.get("retry_after_seconds") if isinstance(exc.details, dict) else None
        if retry is not None:
            headers["Retry-After"] = str(max(0, int(retry)))
        self._send(exc.status, exc.envelope(), headers)

    def _json_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError as exc:
            raise bad_request("Invalid Content-Length.", code="invalid_request") from exc
        if length < 0:
            raise bad_request("Invalid Content-Length.", code="invalid_request")
        if length > self.service.config.max_body_bytes:
            raise too_large()
        if length == 0:
            return {}
        content_type = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if content_type and content_type != "application/json":
            from .errors import unsupported_media

            raise unsupported_media()
        raw = self.rfile.read(length)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise bad_request("Request body must be valid UTF-8 JSON.", code="invalid_json") from exc
        if not isinstance(value, dict):
            raise bad_request("Request body must be a JSON object.", code="invalid_json")
        return value

    def _token(self) -> str | None:
        header = self.headers.get("Authorization") or ""
        if header.lower().startswith("bearer "):
            return header[7:].strip() or None
        alt = self.headers.get("X-HBBS-Token")
        return alt.strip() if alt else None

    def _identity(self) -> dict[str, Any] | None:
        return self.service.authenticate(self._token())

    def _dispatch(self, method: str) -> None:
        try:
            split = urlsplit(self.path)
            segments = _segments(split.path)
            query = parse_qs(split.query, keep_blank_values=True)
            self._route(method, segments, query)
        except HBBSError as exc:
            self._error(exc)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            # Do not leak stack traces, paths or data to clients.
            self._error(HBBSError(500, "internal_error", "Internal server error.", fix="Retry later."))

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_DELETE(self) -> None:  # noqa: N802
        self._dispatch("DELETE")

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch("HEAD")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204, {}, {"Allow": "GET, POST, DELETE, HEAD, OPTIONS"})

    # ------------------------------------------------------------------ routes
    def _route(self, method: str, segments: list[str], query: Mapping[str, list[str]]) -> None:
        if not segments:
            if method in {"GET", "HEAD"}:
                self._send(200, envelope({"service": "hbbs", "contract": CONTRACT, "status": "ok"}))
                return
            raise not_found()
        head = segments[0]
        if head in {"health", "healthz", "ready", "readyz"} and len(segments) == 1:
            if method in {"GET", "HEAD"}:
                self._send(200, envelope({"status": "ok", "contract": CONTRACT}))
                return
            raise not_found()
        if head == "contract" and len(segments) == 1 and method in {"GET", "HEAD"}:
            self._send(200, envelope({"contract": CONTRACT, "boards": ["general", "agents", "holyc", "lore", "announcements"]}))
            return
        if head in {"signup", "register"} and len(segments) == 1 and method == "POST":
            self._send(201, envelope(self.service.signup(self._json_body())))
            return
        if head in {"accounts", "users"}:
            self._route_accounts(method, segments, query)
            return
        if head in {"auth", "login", "logout", "sessions"}:
            self._route_auth(method, segments)
            return
        if head == "me" and len(segments) == 1:
            if method in {"GET", "HEAD"}:
                self._send(200, envelope(self.service.me(self._identity())))
                return
            raise not_found()
        if head == "boards":
            self._route_boards(method, segments, query)
            return
        if head == "posts":
            self._route_posts(method, segments, query)
            return
        if head in {"queue", "mod", "moderation"}:
            self._route_mod(method, segments, query)
            return
        raise not_found()

    def _route_accounts(self, method: str, segments: list[str], query: Mapping[str, list[str]]) -> None:
        if len(segments) == 1:
            if method == "POST":
                self._send(201, envelope(self.service.signup(self._json_body())))
                return
            if method in {"GET", "HEAD"}:
                identity = self._identity()
                self._send(200, envelope(self.service.list_accounts(identity, status=(query.get("status") or [None])[0])))
                return
        if len(segments) == 2 and segments[1] in {"signup", "register"} and method == "POST":
            self._send(201, envelope(self.service.signup(self._json_body())))
            return
        if len(segments) == 2 and segments[1] in {"me", "self"} and method in {"GET", "HEAD"}:
            self._send(200, envelope(self.service.me(self._identity())))
            return
        if len(segments) == 2 and segments[1] in {"login", "token"} and method == "POST":
            self._send(200, envelope(self.service.login(self._json_body())))
            return
        if len(segments) == 2 and not segments[1].isdigit() and method in {"GET", "HEAD"}:
            self._send(200, envelope(self.service.get_account(self._identity(), segments[1])))
            return
        if len(segments) == 2 and segments[1].isdigit() and method in {"GET", "HEAD"}:
            self._send(200, envelope(self.service.get_account(self._identity(), segments[1])))
            return
        if len(segments) >= 3 and segments[1].isdigit() and segments[2] in {"ban", "unban"}:
            account_id = int(segments[1])
            if method != "POST":
                raise not_found()
            if segments[2] == "ban":
                self._send(200, envelope(self.service.ban_account(self._identity(), account_id, self._json_body())))
            else:
                self._send(200, envelope(self.service.unban_account(self._identity(), account_id)))
            return
        raise not_found()

    def _route_auth(self, method: str, segments: list[str]) -> None:
        action = segments[1] if len(segments) > 1 else None
        if segments[0] == "login":
            if method == "POST":
                self._send(200, envelope(self.service.login(self._json_body())))
                return
            raise not_found()
        if segments[0] == "logout":
            if method in {"DELETE", "POST"}:
                self._send(200, envelope(self.service.logout(self._identity() or {})))
                return
            raise not_found()
        if segments[0] == "sessions":
            if action in {None, "current"} and method == "POST":
                self._send(200, envelope(self.service.login(self._json_body())))
                return
            if action in {None, "current"} and method == "DELETE":
                self._send(200, envelope(self.service.logout(self._identity() or {})))
                return
        if segments[0] == "auth":
            if action in {"register", "signup"} and method == "POST":
                self._send(201, envelope(self.service.signup(self._json_body())))
                return
            if action in {None, "login", "token"} and method == "POST":
                self._send(200, envelope(self.service.login(self._json_body())))
                return
            if action in {None, "logout", "session"} and method in {"DELETE", "POST"}:
                self._send(200, envelope(self.service.logout(self._identity() or {})))
                return
            if action in {"me", "whoami"} and method in {"GET", "HEAD"}:
                self._send(200, envelope(self.service.me(self._identity())))
                return
        raise not_found()

    def _route_boards(self, method: str, segments: list[str], query: Mapping[str, list[str]]) -> None:
        if len(segments) == 1:
            if method in {"GET", "HEAD"}:
                self._send(200, envelope(self.service.list_boards()))
                return
            raise not_found()
        board = segments[1]
        if len(segments) == 2:
            if method in {"GET", "HEAD"}:
                boards = self.service.list_boards()["boards"]
                match = next((item for item in boards if item["name"] == board.lower()), None)
                if match is None:
                    raise not_found("Unknown board.", code="unknown_board")
                listing = self.service.list_posts(self._identity(), board, limit=(query.get("limit") or ["25"])[0])
                self._send(200, envelope({"board": match, "posts": listing["posts"], "next_before": listing["next_before"]}))
                return
            raise not_found()
        if len(segments) == 3 and segments[2] in {"posts", "post", "threads", "messages"}:
            if method in {"GET", "HEAD"}:
                limit = (query.get("limit") or ["25"])[0]
                before_raw = (query.get("before") or [None])[0]
                try:
                    before = int(before_raw) if before_raw not in (None, "") else None
                except (TypeError, ValueError) as exc:
                    raise bad_request("'before' must be an integer post id.", code="validation_error") from exc
                self._send(
                    200,
                    envelope(self.service.list_posts(self._identity(), board, limit=limit, before=before)),
                )
                return
            if method == "POST":
                created = self.service.create_post(self._identity(), board, self._json_body())
                self._send(201, envelope(_resource("post", created)))
                return
        raise not_found()

    def _route_posts(self, method: str, segments: list[str], query: Mapping[str, list[str]] | None = None) -> None:
        if len(segments) == 1:
            query = query or {}
            board = (query.get("board") or [None])[0]
            if method in {"GET", "HEAD"}:
                if board:
                    limit = (query.get("limit") or ["25"])[0]
                    before_raw = (query.get("before") or [None])[0]
                    try:
                        before = int(before_raw) if before_raw not in (None, "") else None
                    except (TypeError, ValueError) as exc:
                        raise bad_request("'before' must be an integer post id.", code="validation_error") from exc
                    self._send(200, envelope(self.service.list_posts(self._identity(), board, limit=limit, before=before)))
                    return
                raise bad_request("The 'board' query parameter is required.", code="board_required", details={"field": "board"})
            if method == "POST":
                body = self._json_body()
                body_board = body.get("board")
                if not isinstance(body_board, str) or not body_board:
                    raise bad_request("'board' is required in the body.", code="validation_error", details={"field": "board"})
                created = self.service.create_post(self._identity(), body_board, body)
                self._send(201, envelope(_resource("post", created)))
                return
            raise not_found()
        if not segments[1].isdigit():
            raise not_found()
        post_id = int(segments[1])
        if len(segments) == 2:
            if method in {"GET", "HEAD"}:
                self._send(200, envelope(self.service.get_post(self._identity(), post_id)))
                return
            if method == "DELETE":
                self._send(200, envelope(self.service.hide_post(self._identity(), post_id, self._json_body())))
                return
            raise not_found()
        if len(segments) == 3 and segments[2] in {"flags", "flag", "report"}:
            if method == "POST":
                flag = self.service.flag_post(self._identity(), post_id, self._json_body())
                self._send(201, envelope(_resource("flag", flag)))
                return
            raise not_found()
        if len(segments) == 3 and segments[2] in {"hide", "remove"}:
            if method == "POST":
                self._send(200, envelope(self.service.hide_post(self._identity(), post_id, self._json_body())))
                return
            raise not_found()
        raise not_found()

    def _route_mod(self, method: str, segments: list[str], query: Mapping[str, list[str]]) -> None:
        # Accept /mod/..., /moderation/... and bare /queue.
        parts = segments[1:] if segments[0] in {"mod", "moderation"} else segments
        if not parts:
            raise not_found()
        head = parts[0]
        if head in {"queue", "pending"}:
            if len(parts) == 1 and method in {"GET", "HEAD"}:
                self._send(
                    200,
                    envelope(
                        self.service.mod_queue(
                            self._identity(),
                            kind=(query.get("kind") or [None])[0],
                            state=(query.get("state") or ["pending"])[0],
                        )
                    ),
                )
                return
            if len(parts) >= 3 and parts[1].isdigit() and parts[2] in {"approve", "reject"}:
                body = self._json_body()
                self._send(
                    200,
                    envelope(
                        self.service.resolve_queue(
                            self._identity(),
                            int(parts[1]),
                            approve=parts[2] == "approve",
                            reason=body.get("reason"),
                        )
                    ),
                )
                return
            if len(parts) == 2 and parts[1].isdigit() and method == "POST":
                body = self._json_body()
                action = str(body.get("action") or body.get("decision") or "").lower()
                if action not in {"approve", "reject"}:
                    raise bad_request("Body must contain action='approve' or action='reject'.", code="invalid_action")
                self._send(
                    200,
                    envelope(
                        self.service.resolve_queue(
                            self._identity(),
                            int(parts[1]),
                            approve=action == "approve",
                            reason=body.get("reason"),
                        )
                    ),
                )
                return
        if head in {"flags", "reports"}:
            if len(parts) == 1 and method in {"GET", "HEAD"}:
                self._send(200, envelope(self.service.list_flags(self._identity(), state=(query.get("state") or ["open"])[0])))
                return
            if len(parts) >= 3 and parts[1].isdigit() and parts[2] in {"resolve", "hide", "dismiss", "keep"}:
                action = parts[2]
                body = self._json_body()
                if body.get("action"):
                    action = str(body["action"]).lower()
                self._send(200, envelope(self.service.resolve_flag(self._identity(), int(parts[1]), action=action)))
                return
        if head in {"audit", "log"} and len(parts) == 1 and method in {"GET", "HEAD"}:
            limit = (query.get("limit") or ["100"])[0]
            self._send(200, envelope(self.service.list_audit(self._identity(), limit=limit)))
            return
        if head in {"accounts", "users"}:
            if len(parts) == 1 and method in {"GET", "HEAD"}:
                self._send(
                    200,
                    envelope(self.service.list_accounts(self._identity(), status=(query.get("status") or [None])[0])),
                )
                return
            if len(parts) >= 3 and parts[1].isdigit() and parts[2] in {"ban", "unban"}:
                if method != "POST":
                    raise not_found()
                if parts[2] == "ban":
                    self._send(200, envelope(self.service.ban_account(self._identity(), int(parts[1]), self._json_body())))
                else:
                    self._send(200, envelope(self.service.unban_account(self._identity(), int(parts[1]))))
                return
        if head in {"posts", "threads"}:
            if len(parts) >= 3 and parts[1].isdigit() and parts[2] in {"hide", "remove"} and method == "POST":
                self._send(200, envelope(self.service.hide_post(self._identity(), int(parts[1]), self._json_body())))
                return
            if len(parts) == 1 and method in {"GET", "HEAD"}:
                # Convenience: pending posts are visible through the queue.
                self._send(
                    200,
                    envelope(self.service.mod_queue(self._identity(), kind="post", state=(query.get("state") or ["pending"])[0])),
                )
                return
        raise not_found()


class HBBSServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], service: HBBSService) -> None:
        self.service = service
        super().__init__(address, HBBSRequestHandler)


def make_server(config: Config, service: HBBSService | None = None, *, host: str | None = None, port: int | None = None) -> HBBSServer:
    config.check_bind_safety()
    service = service or HBBSService(config)
    server = HBBSServer((host if host is not None else config.bind_host, config.bind_port if port is None else port), service)
    if config.tls_enabled:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(config.tls_cert, config.tls_key)  # type: ignore[arg-type]
        server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


def serve_forever(config: Config) -> None:
    server = make_server(config)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def start_background(config: Config, service: HBBSService | None = None) -> tuple[HBBSServer, threading.Thread]:
    """Start a server on the configured address for tests and local tools."""
    server = make_server(config, service, host="127.0.0.1", port=0 if config.bind_port == 0 else config.bind_port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread
