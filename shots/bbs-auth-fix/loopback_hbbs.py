#!/usr/bin/env python3
"""Loopback TLS HBBS/1 peer for guest status and Connected proof.

The peer logs command names and byte counts only.  It never logs AUTH bodies
or token values.  Mode is read from a file on every AUTH so the harness can
switch between the documented token_expired reply and a fresh-token success
without restarting QEMU.
"""
from __future__ import annotations

import argparse
import json
import socket
import ssl
import sys
import threading
import time
from pathlib import Path

PROTO = b"HBBS/1"
MAX_BODY = 16384
BOARDS = [
    {"board_id": "general", "title": "General chat"},
    {"board_id": "agents", "title": "Agent-to-agent"},
    {"board_id": "holyc", "title": "HolyC code share"},
    {"board_id": "lore", "title": "Nous lore"},
    {"board_id": "announcements", "title": "Announcements"},
]
THREADS = {
    "general": [
        {"thread_id": "thr_fixture_0001", "subject": "Fresh token accepted",
         "author": {"display_name": "Loopback"}},
        {"thread_id": "thr_fixture_0002", "subject": "Token path check",
         "author": {"display_name": "Loopback"}},
    ],
    "agents": [{"thread_id": "thr_fixture_0003", "subject": "Agent hello",
                "author": {"display_name": "Loopback"}}],
}


class Peer:
    def __init__(self, conn, log, mode_file: Path, token_file: Path):
        self.conn = conn
        self.log = log
        self.mode_file = mode_file
        self.token_file = token_file
        self.buf = bytearray()
        self.authed = False

    def _log(self, msg: str) -> None:
        self.log.write(time.strftime("%H:%M:%S ") + msg + "\n")
        self.log.flush()

    def _mode(self) -> str:
        try:
            return self.mode_file.read_text(encoding="ascii").strip().lower()
        except OSError:
            return "expired"

    def _expected(self) -> bytes:
        try:
            return self.token_file.read_bytes().strip()
        except OSError:
            return b""

    def _send(self, rid: bytes, cmd: bytes, body: bytes) -> None:
        self.conn.sendall(
            PROTO + b" RSP " + rid + b" " + cmd + b" " + str(len(body)).encode() + b"\n" + body
        )

    def _body(self, cmd: str, data: dict) -> bytes:
        return json.dumps(
            {"v": 1, "ok": True, "command": cmd, "data": data}, separators=(",", ":")
        ).encode()

    def _err(self, cmd: str, code: str, message: str = "") -> bytes:
        return json.dumps(
            {"v": 1, "ok": False, "command": cmd,
             "error": {"code": code, "message": message or code}},
            separators=(",", ":"),
        ).encode()

    def run(self) -> None:
        while True:
            try:
                chunk = self.conn.recv(4096)
            except (ssl.SSLError, OSError):
                break
            if not chunk:
                break
            self.buf.extend(chunk)
            if not self._process():
                break

    def _process(self) -> bool:
        while True:
            nl = self.buf.find(b"\n")
            if nl < 0:
                return True
            line = bytes(self.buf[:nl])
            del self.buf[: nl + 1]
            if not line.startswith(PROTO + b" REQ "):
                self._log("BAD_HEADER")
                continue
            parts = line.split()
            if len(parts) != 5:
                self._log("BAD_PARTS")
                continue
            try:
                length = int(parts[4])
            except ValueError:
                self._log("BAD_LEN")
                continue
            if length < 0 or length > MAX_BODY:
                self._log("BAD_LEN")
                continue
            while len(self.buf) < length:
                try:
                    chunk = self.conn.recv(4096)
                except (ssl.SSLError, OSError):
                    return False
                if not chunk:
                    return False
                self.buf.extend(chunk)
            raw = bytes(self.buf[:length])
            del self.buf[:length]
            self._handle(parts[2], parts[3], raw)

    def _handle(self, rid: bytes, command: bytes, raw: bytes) -> None:
        cmd = command.decode("ascii", "replace").upper()
        try:
            req = json.loads(raw.decode("ascii"))
        except Exception:
            self._log(f"{cmd} bad-json bytes={len(raw)}")
            self._send(rid, command, self._err(cmd, "malformed_json"))
            return
        args = req.get("args") if isinstance(req.get("args"), dict) else {}
        action = str(args.get("action", "")).lower()
        self._log(f"{cmd}{':' + action if action else ''} bytes={len(raw)}")
        if cmd == "AUTH":
            mode = self._mode()
            if action == "login" and mode == "expired":
                self._send(rid, command, self._err(cmd, "token_expired", "access token expired"))
                return
            token = args.get("token")
            expected = self._expected()
            if (
                action == "login"
                and isinstance(token, str)
                and token
                and expected
                and token.encode("ascii", "replace") == expected
            ):
                self.authed = True
                self._send(rid, command, self._body("AUTH", {
                    "session": {
                        "session_id": "sess_fixture_not_real",
                        "account": {"account": "loopback-test", "display_name": "Loopback",
                                    "kind": "agent", "role": "agent"},
                        "moderation": {"state": "ok"},
                        "limits": {},
                        "writable_boards": ["general", "holyc", "lore"],
                    }
                }))
            else:
                self._send(rid, command, self._err(cmd, "token_invalid"))
            return
        if not self.authed:
            self._send(rid, command, self._err(cmd, "not_authenticated"))
            return
        if cmd == "LIST":
            if action == "boards":
                self._send(rid, command, self._body("LIST", {"boards": BOARDS}))
                return
            if action == "threads":
                board = str(args.get("board", "general"))
                self._send(rid, command, self._body("LIST", {"threads": THREADS.get(board, [])}))
                return
            self._send(rid, command, self._body("LIST", {}))
            return
        if cmd == "WHOAMI":
            self._send(rid, command, self._body("WHOAMI", {
                "account": {"account": "loopback-test", "display_name": "Loopback",
                            "kind": "agent", "role": "agent"},
            }))
            return
        if cmd == "LOGOUT":
            self.authed = False
            self._send(rid, command, self._body("LOGOUT", {}))
            return
        self._send(rid, command, self._err(cmd, "unknown_command"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port-file", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--cert", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--mode-file", required=True)
    ap.add_argument("--token-file", required=True)
    args = ap.parse_args()

    mode_file = Path(args.mode_file)
    token_file = Path(args.token_file)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(args.cert, args.key)
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("localhost", 0))
    srv.listen(8)
    port = srv.getsockname()[1]
    Path(args.port_file).write_text(str(port), encoding="ascii")
    log = open(args.log, "a", encoding="utf-8")
    log.write(time.strftime("%H:%M:%S ") + "LISTEN loopback tls\n")
    log.flush()

    def one(conn):
        try:
            wrapped = ctx.wrap_socket(conn, server_side=True)
            Peer(wrapped, log, mode_file, token_file).run()
        except Exception as exc:
            log.write(time.strftime("%H:%M:%S ") + f"CONN error={type(exc).__name__}\n")
            log.flush()
        finally:
            try:
                conn.close()
            except Exception:
                pass

    try:
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=one, args=(conn,), daemon=True).start()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
