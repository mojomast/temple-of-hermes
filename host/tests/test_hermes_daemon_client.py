"""Tests for host/hermes_daemon_client.py using an in-memory fake serial port."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from host.hermes_daemon_client import (  # noqa: E402
    HermesDaemonClient,
    HermesRemoteError,
    MAX_PAYLOAD,
)

BEACON = b"HBEACON TempleOfHermes/0.1.0\n"


def frame(kind: str, ident: int | str, status: str, payload: bytes) -> bytes:
    return f"{kind} {ident} {status} {len(payload)}\n".encode() + payload


def event(seq: int, kind: str, data: dict) -> bytes:
    payload = json.dumps(data).encode()
    return f"HEVT {seq} {kind} {len(payload)}\n".encode() + payload


class FakeDaemon:
    """Small guest-side model of the Hermes ops used by the client tests."""

    def __init__(self) -> None:
        self.docs: dict[str, bytes] = {}
        self.files: dict[str, bytes] = {"/Welcome.DD": b"DolDoc text"}
        self.mode = "user"
        self.calls: list[tuple[str, bytes]] = []

    def reply(self, rid: int, obj) -> bytes:
        if isinstance(obj, bytes):
            data = obj
        else:
            data = json.dumps(obj).encode()
        return frame("HRPL", rid, "ok", data)

    def error(self, rid: int, reason: str) -> bytes:
        return frame("HRPL", rid, "err", reason.encode())

    def handle(self, op: str, payload: bytes, rid: int) -> list[bytes]:
        self.calls.append((op, payload))
        if op == "ping":
            return [self.reply(rid, {"pong": 1, "t": 1.5, "mode": self.mode,
                                     "version": "0.1.0"})]
        if op == "help":
            return [self.reply(rid, {
                "name": "TempleOfHermes", "version": "0.1.0",
                "ops": ["ping", "eval", "tasks", "windows", "task_kill",
                        "doc_read", "doc_write", "toast", "guards", "sysinfo",
                        "stat", "ls", "list"],
            })]
        if op == "eval":
            if b"bad(" in payload:
                text = "Compile Error: near '(' on line 3 col 7\n"
                return [self.reply(rid, {
                    "ok": 0, "text": text,
                    "error": {"kind": "compile", "code": 67, "line": 3,
                              "col": 7, "message": text},
                })]
            return [self.reply(rid, {"ok": 1, "text": "2", "error": None})]
        if op in ("tasks", "task_list"):
            return [self.reply(rid, {
                "focus": "0x1000",
                "tasks": [
                    {"addr": "0x1000", "name": "adam", "title": "Adam",
                     "win": [0, 0, 79, 59], "show": 1, "focus": 1,
                     "is_window": 1},
                    {"addr": "0x2000", "name": "doc", "title": "Welcome",
                     "win": [5, 5, 60, 20], "show": 1, "focus": 0,
                     "is_window": 1},
                ],
            })]
        if op == "windows":
            evt = event(7, "window_opened", {"title": "Welcome"})
            return [evt, self.reply(rid, {
                "focus": "0x1000",
                "windows": [{"addr": "0x1000", "title": "Adam",
                             "win": [0, 0, 79, 59], "focus": 1, "z": 2}],
            })]
        if op in ("focus", "window_focus"):
            if payload and payload not in (b"0x1000", b"0x2000", b"Welcome"):
                return [self.error(rid, "no_task")]
            key = "windows" if op == "window_focus" else "tasks"
            obj = {"focus": "0x2000", key: []}
            return [self.reply(rid, obj)]
        if op == "task_kill":
            if payload in (b"0x1000", b"Adam", b"HermesDaemon"):
                return [self.error(rid, "protected_task")]
            return [self.reply(rid, {"ok": 1, "killed": 1,
                                     "addr": "0x2000", "title": "Welcome"})]
        if op in ("list", "ls"):
            return [self.reply(rid, [
                {"name": "Hermes", "is_dir": 1, "size": 0,
                 "attr": 16, "datetime": 0},
                {"name": "Daemon.HC", "is_dir": 0, "size": 1234,
                 "attr": 0, "datetime": 99},
            ])]
        if op == "stat":
            if payload == b"/Adam/Hermes":
                return [self.reply(rid, {"path": "/Adam/Hermes", "exists": 1,
                                         "name": "Hermes", "size": 0,
                                         "attr": 16, "is_dir": 1,
                                         "datetime": 0})]
            return [self.reply(rid, {"path": payload.decode(), "exists": 0})]
        if op == "doc_read":
            if not payload:
                return [self.reply(rid, {"ok": 1, "path": "focus", "size": 5,
                                         "dol": "$$FG$$hi", "text": "hi"})]
            data = self.docs.get(payload.decode())
            if data is None:
                return [self.reply(rid, {"ok": 0, "error": "doc_read"})]
            return [self.reply(rid, {"ok": 1, "path": payload.decode(),
                                     "size": len(data),
                                     "dol": data.decode(), "text": data.decode()})]
        if op == "doc_write":
            path, _, body = payload.partition(b"\0")
            self.docs[path.decode()] = body
            return [self.reply(rid, {"ok": 1, "wrote": len(body),
                                     "path": path.decode()})]
        if op == "toast":
            text = payload.decode()
            if not text.startswith("Hermes says"):
                text = "Hermes says: " + text
            return [self.reply(rid, {"ok": 1, "toast": text, "until": 9.5})]
        if op == "guards":
            what = payload.decode() or "Fmt"
            allow = self.mode == "user" or (what == "YorN" and self.mode == "shared")
            return [self.reply(rid, {
                "mode": self.mode, "safe_mode": self.mode != "user",
                "what": what, "allow": int(allow), "input_gate": 1,
                "guard_installed": 1, "yorn_blocked": int(self.mode == "agent"),
            })]
        if op == "sysinfo":
            return [self.reply(rid, {
                "name": "TempleOfHermes", "version": "0.1.0",
                "mode": self.mode, "tasks": 2, "windows": 1,
                "screen": {"w": 640, "h": 480, "cols": 80, "rows": 60},
                "com": {"port": 1, "baud": 115200},
            })]
        if op == "pull":
            data = self.files.get(payload.decode())
            if data is None:
                return [self.error(rid, "pull_read")]
            return [self.reply(rid, data)]
        if op == "push":
            path, _, body = payload.partition(b"\0")
            self.files[path.decode()] = body
            return [self.reply(rid, {"wrote": len(body)})]
        if op == "events":
            return [self.reply(rid, [])]
        if op == "idle":
            return [self.reply(rid, {"t": 2.0, "mode": self.mode,
                                     "prompt": 0, "evt_pending": 0,
                                     "ready": 1})]
        if op == "clip_get":
            return [self.reply(rid, {"text": "clip"})]
        if op == "clip_set":
            return [self.reply(rid, {"text": payload.decode()})]
        if op == "mode":
            self.mode = payload.decode()
            return [self.reply(rid, {"mode": self.mode})]
        if op == "mouse":
            return [self.reply(rid, {"x": 1, "y": 2, "mode": self.mode})]
        if op == "text":
            return [self.reply(rid, {"title": "Adam", "text": "hello"})]
        return [self.error(rid, "unknown_op")]


class FakeSerial:
    """In-memory serial transport that feeds a FakeDaemon and returns frames."""

    def __init__(self, daemon: FakeDaemon, chunk_size: int = 65536,
                 beacon: bool = True):
        self.daemon = daemon
        self.chunk_size = chunk_size
        self.inbuf = b""
        self.out = bytearray(BEACON if beacon else b"")
        self.closed = False
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.writes.append(data)
        self.inbuf += data
        while True:
            nl = self.inbuf.find(b"\n")
            if nl < 0:
                return
            line = self.inbuf[:nl]
            parts = line.split()
            if len(parts) < 4 or parts[0] != b"HREQ":
                self.inbuf = self.inbuf[nl + 1:]
                continue
            try:
                rid = int(parts[1])
                length = int(parts[3])
            except ValueError:
                self.inbuf = self.inbuf[nl + 1:]
                continue
            if len(self.inbuf) < nl + 1 + length:
                return
            payload = self.inbuf[nl + 1:nl + 1 + length]
            self.inbuf = self.inbuf[nl + 1 + length:]
            for out in self.daemon.handle(parts[2].decode(), payload, rid):
                self.out.extend(out)

    def read(self, timeout: float) -> bytes:
        if not self.out:
            return b""
        n = min(self.chunk_size, len(self.out))
        data = bytes(self.out[:n])
        del self.out[:n]
        return data

    def close(self) -> None:
        self.closed = True


def make_client(chunk_size: int = 65536) -> tuple[HermesDaemonClient, FakeDaemon, FakeSerial]:
    daemon = FakeDaemon()
    serial = FakeSerial(daemon, chunk_size=chunk_size)
    return HermesDaemonClient(transport=serial, timeout=2.0), daemon, serial


def test_beacon_and_ping():
    client, _, _ = make_client()
    assert client.wait_beacon(1.0) == "HBEACON TempleOfHermes/0.1.0"
    pong = client.ping()
    assert pong["pong"] == 1
    assert pong["version"] == "0.1.0"
    assert client.beacons[-1].startswith("HBEACON")


def test_help_lists_new_ops():
    client, _, _ = make_client()
    ops = client.help()["ops"]
    for name in ("windows", "task_kill", "doc_read", "doc_write",
                 "toast", "guards", "sysinfo", "stat", "ls"):
        assert name in ops


def test_eval_ok_and_structured_error():
    client, _, _ = make_client()
    assert client.eval("6*7") == {"ok": 1, "text": "2", "error": None}
    bad = client.eval("bad(")
    assert bad["ok"] == 0
    assert bad["error"]["kind"] == "compile"
    assert bad["error"]["line"] == 3
    assert bad["error"]["col"] == 7
    assert "Compile Error" in bad["error"]["message"]


def test_structured_list_and_stat():
    client, _, _ = make_client()
    entries = client.ls("/Adam")
    assert entries[0]["name"] == "Hermes"
    assert entries[0]["is_dir"] == 1
    assert entries[1]["size"] == 1234
    assert client.stat("/Adam/Hermes")["exists"] == 1
    assert client.stat("/nope") == {"path": "/nope", "exists": 0}


def test_windows_focus_and_task_kill_guard():
    client, _, _ = make_client()
    w = client.windows()
    assert w["windows"][0]["title"] == "Adam"
    # A window_opened HEVT arrived before the HRPL frame.
    assert client.events[-1].kind == "window_opened"
    assert client.take_events()[0]["data"]["title"] == "Welcome"
    assert client.window_focus("0x2000")["focus"] == "0x2000"
    with pytest.raises(HermesRemoteError) as exc:
        client.task_kill("HermesDaemon")
    assert exc.value.reason == "protected_task"
    assert client.task_kill("0x2000")["killed"] == 1


def test_doc_read_write_roundtrip():
    client, daemon, _ = make_client()
    assert client.doc_read()["text"] == "hi"
    wrote = client.doc_write("/Tmp/Note.DD", "$$FG,YELLOW$$Hello")
    assert wrote["wrote"] == len("$$FG,YELLOW$$Hello")
    got = client.doc_read("/Tmp/Note.DD")
    assert got["dol"] == "$$FG,YELLOW$$Hello"
    assert daemon.docs["/Tmp/Note.DD"] == b"$$FG,YELLOW$$Hello"


def test_toast_prefix_and_guards_and_sysinfo():
    client, daemon, _ = make_client()
    assert client.toast("safe to continue")["toast"].startswith("Hermes says:")
    assert client.guards("Fmt")["allow"] == 1
    daemon.mode = "agent"
    g = client.guards("YorN")
    assert g["safe_mode"] == 1 and g["allow"] == 0 and g["yorn_blocked"] == 1
    info = client.sysinfo()
    assert info["screen"] == {"w": 640, "h": 480, "cols": 80, "rows": 60}


def test_error_frames_raise():
    client, _, _ = make_client()
    with pytest.raises(HermesRemoteError) as exc:
        client.window_focus("does-not-exist")
    assert exc.value.reason == "no_task"


def test_partial_serial_reads_still_parse():
    client, _, _ = make_client(chunk_size=3)
    assert client.ping()["pong"] == 1
    assert client.stat("/Adam/Hermes")["is_dir"] == 1


def test_pull_push_binary_payloads():
    client, daemon, serial = make_client()
    assert client.pull("/Welcome.DD") == b"DolDoc text"
    body = bytes(range(32))
    assert client.push("/Tmp/Bin.DAT", body)["wrote"] == 32
    assert daemon.files["/Tmp/Bin.DAT"] == body
    # The length prefix is exact even with NUL bytes in the payload.
    assert serial.writes[-1].endswith(body)


def test_payload_limit_and_bad_op():
    client, _, _ = make_client()
    with pytest.raises(ValueError):
        client.request("ping", b"x" * (MAX_PAYLOAD + 1))
    with pytest.raises(ValueError):
        client.request("bad op")


def test_idle_and_clipboard_preserved():
    client, _, _ = make_client()
    assert client.idle()["ready"] == 1
    assert client.clip_set("copied")["text"] == "copied"
    assert client.clip_get()["text"] == "clip"
    assert client.mouse(10, 20)["x"] == 1
