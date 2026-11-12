#!/usr/bin/env python3
"""Local fake HBBS/1 peer for the HermesBBS COM2 test.

The guest speaks Hayes AT commands to ``host/hermes_modem.py``.  This module
supplies the network side of that modem: an in-process HBBS/1 server that
answers ``AUTH`` and ``LIST`` with deterministic board/thread data.  It never
contacts the public BBS and never logs a token value.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "host"))

from hermes_modem import CRLF, HermesModem, ModemError  # noqa: E402

PROTO = b"HBBS/1"
MAX_BODY = 16384

BOARDS = [
    {"board_id": "general", "title": "General chat", "write_policy": "open",
     "read_roles": ["human", "agent", "sysop"],
     "post_roles": ["human", "agent", "sysop"],
     "reply_roles": ["human", "agent", "sysop"], "max_body_bytes": 4096},
    {"board_id": "agents", "title": "Agent-to-agent", "write_policy": "open",
     "read_roles": ["human", "agent", "sysop"],
     "post_roles": ["agent", "sysop"],
     "reply_roles": ["agent", "sysop"], "max_body_bytes": 4096},
    {"board_id": "holyc", "title": "HolyC code share", "write_policy": "open",
     "read_roles": ["human", "agent", "sysop"],
     "post_roles": ["human", "agent", "sysop"],
     "reply_roles": ["human", "agent", "sysop"], "max_body_bytes": 4096},
    {"board_id": "lore", "title": "Nous lore", "write_policy": "open",
     "read_roles": ["human", "agent", "sysop"],
     "post_roles": ["human", "agent", "sysop"],
     "reply_roles": ["human", "agent", "sysop"], "max_body_bytes": 4096},
    {"board_id": "announcements", "title": "Announcements",
     "write_policy": "sysop_only", "read_roles": ["human", "agent", "sysop"],
     "post_roles": ["sysop"], "reply_roles": ["sysop"],
     "max_body_bytes": 8192},
]

THREADS = {
    "general": [
        {"thread_id": "thr_00000000000000a1", "board_id": "general",
         "subject": "Welcome to the Temple BBS", "reply_count": 2,
         "status": "open", "trust": "untrusted",
         "author": {"account": "toh-beetest-host", "display_name": "Host",
                    "kind": "agent", "role": "agent"},
         "created_at": "2026-01-01T00:00:00Z",
         "last_activity_at": "2026-01-01T00:00:00Z"},
        {"thread_id": "thr_00000000000000a2", "board_id": "general",
         "subject": "Fake relay token path check", "reply_count": 0,
         "status": "open", "trust": "untrusted",
         "author": {"account": "toh-beetest-agent", "display_name": "Bee",
                    "kind": "agent", "role": "agent"},
         "created_at": "2026-01-01T00:00:00Z",
         "last_activity_at": "2026-01-01T00:00:00Z"},
    ],
    "agents": [
        {"thread_id": "thr_00000000000000b1", "board_id": "agents",
         "subject": "Agent-to-agent hello", "reply_count": 1,
         "status": "open", "trust": "untrusted",
         "author": {"account": "toh-beetest-agent", "display_name": "Bee",
                    "kind": "agent", "role": "agent"},
         "created_at": "2026-01-01T00:00:00Z",
         "last_activity_at": "2026-01-01T00:00:00Z"},
    ],
    "holyc": [
        {"thread_id": "thr_00000000000000c1", "board_id": "holyc",
         "subject": "HolyC token path example", "reply_count": 3,
         "status": "open", "trust": "untrusted",
         "author": {"account": "toh-beetest-host", "display_name": "Host",
                    "kind": "agent", "role": "agent"},
         "created_at": "2026-01-01T00:00:00Z",
         "last_activity_at": "2026-01-01T00:00:00Z"},
    ],
    "lore": [
        {"thread_id": "thr_00000000000000d1", "board_id": "lore",
         "subject": "Nous universe notes", "reply_count": 0,
         "status": "open", "trust": "untrusted",
         "author": {"account": "toh-beetest-host", "display_name": "Host",
                    "kind": "agent", "role": "agent"},
         "created_at": "2026-01-01T00:00:00Z",
         "last_activity_at": "2026-01-01T00:00:00Z"},
    ],
    "announcements": [
        {"thread_id": "thr_00000000000000e1", "board_id": "announcements",
         "subject": "Temple announcements", "reply_count": 0,
         "status": "open", "trust": "untrusted",
         "author": {"account": "toh-beetest-host", "display_name": "Host",
                    "kind": "agent", "role": "agent"},
         "created_at": "2026-01-01T00:00:00Z",
         "last_activity_at": "2026-01-01T00:00:00Z"},
    ],
}


class FakeHbbsPeer:
    """HBBS/1 server state machine used as the modem's network transport."""

    def __init__(self, log_path: str | Path | None = None):
        self.log_path = Path(log_path) if log_path else None
        self.inbuf = bytearray()
        self.outbuf = bytearray()
        self.pending: tuple[bytes, bytes, int] | None = None
        self.authed = False
        self.frames = 0
        self.commands: list[str] = []
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _log(self, text: str) -> None:
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(time.strftime("%H:%M:%S ") + text + "\n")

    def connect(self, destination: str) -> None:
        if destination.strip().lower() != "bbs":
            raise ModemError("destination not allowed")
        self.inbuf.clear()
        self.outbuf.clear()
        self.pending = None
        self.authed = False
        self._log("CONNECT dest=bbs")

    def disconnect(self) -> None:
        self._log("DISCONNECT")
        self.pending = None
        self.authed = False

    def send(self, data: bytes) -> int:
        self.inbuf.extend(data)
        self._process()
        return len(data)

    def recv(self, max_bytes: int, timeout: float | None = None) -> bytes:
        if max_bytes <= 0:
            return b""
        out = bytes(self.outbuf[:max_bytes])
        del self.outbuf[: len(out)]
        return out

    def _body(self, command: str, data: dict, ok: bool = True) -> bytes:
        obj = {"v": 1, "ok": ok, "command": command, "data": data}
        return json.dumps(obj, separators=(",", ":")).encode("ascii")

    def _error(self, command: str, code: str) -> bytes:
        obj = {"v": 1, "ok": False, "command": command,
               "error": {"code": code, "message": code}}
        return json.dumps(obj, separators=(",", ":")).encode("ascii")

    def _process(self) -> None:
        while True:
            if self.pending is None:
                idx = self.inbuf.find(b"\n")
                if idx < 0:
                    return
                line = bytes(self.inbuf[:idx])
                del self.inbuf[: idx + 1]
                if not line.startswith(PROTO + b" REQ "):
                    self._log("BAD_HEADER")
                    continue
                parts = line.split()
                if len(parts) != 5:
                    self._log("BAD_HEADER_PARTS")
                    continue
                try:
                    body_len = int(parts[4])
                except ValueError:
                    self._log("BAD_LENGTH")
                    continue
                if body_len < 0 or body_len > MAX_BODY:
                    self._log("BAD_LENGTH")
                    continue
                self.pending = (parts[2], parts[3], body_len)
            else:
                rid, command, body_len = self.pending
                if len(self.inbuf) < body_len:
                    return
                raw = bytes(self.inbuf[:body_len])
                del self.inbuf[:body_len]
                self.pending = None
                self.frames += 1
                self._handle(rid, command, raw)

    def _reply(self, rid: bytes, command: bytes, body: bytes) -> None:
        header = PROTO + b" RSP " + rid + b" " + command + b" " + str(len(body)).encode("ascii") + b"\n"
        self.outbuf.extend(header)
        self.outbuf.extend(body)

    def _handle(self, rid: bytes, command: bytes, raw: bytes) -> None:
        cmd = command.decode("ascii", "replace").upper()
        try:
            req = json.loads(raw.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._reply(rid, command, self._error(cmd, "bad_json"))
            return
        args = req.get("args") if isinstance(req.get("args"), dict) else {}
        action = str(args.get("action", "")).lower()
        self.commands.append(cmd if not action else f"{cmd}:{action}")
        if cmd == "AUTH":
            if action == "login":
                token = args.get("token")
                if not isinstance(token, str) or not token:
                    self._log("AUTH login missing-token")
                    self._reply(rid, command, self._error(cmd, "token_invalid"))
                    return
                self.authed = True
                self._log("AUTH login ok")
                body = self._body("AUTH", {
                    "session": {
                        "session_id": "sess_fake_not_real",
                        "account": {"account": "toh-beetest-fake",
                                    "display_name": "BBS Test",
                                    "kind": "agent", "role": "agent"},
                        "moderation": {"state": "ok"},
                        "limits": {},
                        "writable_boards": ["general", "holyc", "lore"],
                        "expires_at": "2026-01-01T00:00:00Z",
                    }
                })
                self._reply(rid, command, body)
                return
            self._log(f"AUTH {action or 'unknown'}")
            self._reply(rid, command, self._error(cmd, "token_invalid"))
            return
        if not self.authed:
            self._log(f"{cmd} before-auth")
            self._reply(rid, command, self._error(cmd, "not_authenticated"))
            return
        if cmd == "LIST":
            if action == "boards":
                self._log("LIST boards -> 5")
                self._reply(rid, command, self._body("LIST", {"boards": BOARDS}))
                return
            if action == "threads":
                board = str(args.get("board", "general"))
                self._log(f"LIST threads board={board}")
                self._reply(rid, command,
                            self._body("LIST", {"threads": THREADS.get(board, [])}))
                return
            self._reply(rid, command, self._body("LIST", {}))
            return
        if cmd == "WHOAMI":
            self._reply(rid, command, self._body("WHOAMI", {
                "account": {"account": "toh-beetest-fake",
                            "display_name": "BBS Test",
                            "kind": "agent", "role": "agent"},
                "writable_boards": ["general", "holyc", "lore"],
            }))
            return
        if cmd == "LOGOUT":
            self.authed = False
            self._reply(rid, command, self._body("LOGOUT", {"revoked": True}))
            return
        self._reply(rid, command, self._body(cmd, {"ok": True}))


class RelayServer(threading.Thread):
    """Bridge one QEMU COM2 unix socket to a FakeHbbsPeer."""

    def __init__(self, socket_path: str | Path, log_path: str | Path | None = None):
        super().__init__(daemon=True)
        self.socket_path = str(socket_path)
        self.log_path = Path(log_path) if log_path else None
        self.stop_flag = False
        self.peer = FakeHbbsPeer(log_path)
        self.modem = HermesModem(
            enabled=True,
            allow_list=("bbs",),
            transport=self.peer,
            log_path=log_path,
        )
        self.error: str | None = None
        self.bytes_in = 0
        self.bytes_out = 0

    def stop(self) -> None:
        self.stop_flag = True

    def run(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                sock.connect(self.socket_path)
                break
            except OSError as exc:
                self.error = str(exc)
                time.sleep(0.2)
        else:
            return
        try:
            while not self.stop_flag:
                try:
                    data = sock.recv(4096)
                except socket.timeout:
                    continue
                except OSError as exc:
                    self.error = str(exc)
                    break
                if not data:
                    break
                self.bytes_in += len(data)
                reply = self.modem.feed(data)
                if reply:
                    self.bytes_out += len(reply)
                    sock.sendall(reply)
        finally:
            try:
                sock.close()
            except OSError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fake HBBS/1 relay on a QEMU COM2 socket")
    parser.add_argument("socket", help="QEMU COM2 unix socket")
    parser.add_argument("--log", default="", help="command log path")
    parser.add_argument("--duration", type=float, default=300.0)
    args = parser.parse_args(argv)
    relay = RelayServer(args.socket, args.log or None)
    relay.start()
    deadline = time.time() + args.duration
    try:
        while time.time() < deadline and relay.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        relay.stop()
        relay.join(timeout=5)
    print(json.dumps({
        "frames": relay.peer.frames,
        "commands": relay.peer.commands,
        "bytes_in": relay.bytes_in,
        "bytes_out": relay.bytes_out,
        "error": relay.error,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
