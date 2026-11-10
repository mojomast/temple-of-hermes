#!/usr/bin/env python3
"""Host client for THE TEMPLE OF HERMES COM1 daemon.

The wire protocol is the one documented in docs/HERMES-FEATURES.md:

    HBEACON <name>/<version>\\n
    HREQ <id> <op> <len>\\n + <len bytes>
    HRPL <id> <ok|err> <len>\\n + <len bytes>
    HEVT <seq> <kind> <len>\\n + <len bytes>

This module deliberately keeps the transport injectable so tests can run
against an in-memory fake serial port.  For a real QEMU instance use
:class:`UnixSocketTransport` with the QEMU COM1 unix socket path.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Protocol

MAX_PAYLOAD = 262144
DEFAULT_TIMEOUT = 60.0


class HermesError(RuntimeError):
    """Base error for client-side failures."""


class HermesRemoteError(HermesError):
    """The guest answered ``HRPL ... err ...``."""

    def __init__(self, op: str, reason: str):
        self.op = op
        self.reason = reason
        super().__init__(f"guest rejected {op}: {reason}")


class HermesProtocolError(HermesError):
    """A frame was malformed or a reply never arrived."""


class Transport(Protocol):
    def write(self, data: bytes) -> None: ...

    def read(self, timeout: float) -> bytes: ...

    def close(self) -> None: ...


class UnixSocketTransport:
    """QEMU ``-serial unix:<path>,server=on`` adapter."""

    def __init__(self, path: str, timeout: float = DEFAULT_TIMEOUT):
        self.path = str(path)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        deadline = time.time() + timeout
        last: Exception | None = None
        while time.time() < deadline:
            try:
                self.sock.connect(self.path)
                break
            except OSError as exc:  # pragma: no cover - timing dependent
                last = exc
                time.sleep(0.1)
        else:  # pragma: no cover - timing dependent
            raise HermesError(f"connect {self.path}: {last}")
        self.closed = False

    def write(self, data: bytes) -> None:
        self.sock.sendall(data)

    def read(self, timeout: float) -> bytes:
        self.sock.settimeout(timeout)
        try:
            return self.sock.recv(65536) or b""
        except socket.timeout:
            return b""

    def close(self) -> None:
        self.closed = True
        try:
            self.sock.close()
        except OSError:
            pass


@dataclass
class Event:
    seq: int
    kind: str
    data: Any
    raw: bytes

    def as_dict(self) -> dict[str, Any]:
        return {"seq": self.seq, "kind": self.kind, "data": self.data}


class HermesDaemonClient:
    """Line-framed, length-prefixed client for the Hermes COM1 daemon."""

    def __init__(
        self,
        path: str | None = None,
        *,
        transport: Transport | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        if transport is None:
            if path is None:
                raise ValueError("path or transport is required")
            transport = UnixSocketTransport(path, timeout=timeout)
        self.transport = transport
        self.timeout = timeout
        self.buf = b""
        self.next_id = 1
        self.beacons: list[str] = []
        self.events: list[Event] = []
        self._responses: dict[int, tuple[str, bytes]] = {}

    # -- lifecycle -----------------------------------------------------
    def close(self) -> None:
        self.transport.close()

    def __enter__(self) -> "HermesDaemonClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- framing -------------------------------------------------------
    def _consume(self) -> None:
        prefixes = (b"HBEACON ", b"HEVT ", b"HRPL ")
        while True:
            hits = [(self.buf.find(p), p) for p in prefixes]
            hits = [(i, p) for i, p in hits if i >= 0]
            if not hits:
                # Bound leading junk from a noisy serial line.
                if len(self.buf) > 8192 and not any(
                    p.startswith(self.buf[-1:]) for p in prefixes
                ):
                    self.buf = self.buf[-4096:]
                return
            i, prefix = min(hits, key=lambda item: item[0])
            if i:
                self.buf = self.buf[i:]
            nl = self.buf.find(b"\n")
            if nl < 0:
                return
            line = self.buf[:nl]
            rest = self.buf[nl + 1 :]
            if prefix == b"HBEACON ":
                self.beacons.append(line.decode("ascii", "replace").strip())
                self.buf = rest
                continue
            parts = line.decode("ascii", "replace").split()
            if len(parts) < 4:
                self.buf = rest
                continue
            try:
                length = int(parts[3])
            except ValueError:
                self.buf = rest
                continue
            if length < 0 or length > MAX_PAYLOAD:
                raise HermesProtocolError(f"bad frame length {length!r}: {line!r}")
            if len(rest) < length:
                return
            payload, self.buf = rest[:length], rest[length:]
            if parts[0] == "HEVT":
                self.events.append(self._event(parts, payload))
            else:
                rid = int(parts[1])
                self._responses[rid] = (parts[2], payload)

    @staticmethod
    def _event(parts: list[str], payload: bytes) -> Event:
        try:
            seq = int(parts[1])
        except ValueError:
            seq = 0
        kind = parts[2]
        try:
            data: Any = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            data = payload.decode("utf-8", "replace")
        return Event(seq=seq, kind=kind, data=data, raw=payload)

    def _pump(self, timeout: float) -> None:
        chunk = self.transport.read(timeout)
        if chunk:
            self.buf += chunk
        self._consume()

    def drain(self, seconds: float = 0.4) -> None:
        """Read whatever arrives for ``seconds`` (events and beacons)."""
        deadline = time.time() + max(0.0, seconds)
        while time.time() < deadline:
            self._pump(min(0.15, max(0.0, deadline - time.time())))

    def wait_beacon(self, timeout: float = DEFAULT_TIMEOUT) -> str:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.beacons:
                return self.beacons[-1]
            self._pump(min(1.0, max(0.05, deadline - time.time())))
        raise TimeoutError(
            f"no HBEACON in {timeout:g}s; tail={self.buf[-200:]!r}"
        )

    # -- request/reply ------------------------------------------------
    def request(
        self, op: str, payload: bytes | str = b"", timeout: float | None = None
    ) -> tuple[str, bytes]:
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        if not op or any(c.isspace() for c in op) or not op.isascii():
            raise ValueError(f"invalid op {op!r}")
        if len(payload) > MAX_PAYLOAD:
            raise ValueError(f"payload too large ({len(payload)} bytes)")
        rid = self.next_id
        self.next_id += 1
        header = f"HREQ {rid} {op} {len(payload)}\n".encode("ascii")
        self.transport.write(header + payload)
        deadline = time.time() + (self.timeout if timeout is None else timeout)
        while time.time() < deadline:
            if rid in self._responses:
                status, data = self._responses.pop(rid)
                return status, data
            self._pump(min(1.0, max(0.05, deadline - time.time())))
        raise TimeoutError(f"no HRPL for {op!r} id={rid}; tail={self.buf[-200:]!r}")

    def call(
        self, op: str, payload: bytes | str = b"", timeout: float | None = None
    ) -> Any:
        status, data = self.request(op, payload, timeout=timeout)
        if status != "ok":
            raise HermesRemoteError(op, data.decode("utf-8", "replace").strip())
        if not data:
            return None
        try:
            return json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return data.decode("utf-8", "replace")

    # -- daemon operations --------------------------------------------
    def ping(self, timeout: float | None = None) -> dict[str, Any]:
        return self.call("ping", timeout=timeout)

    def help(self, timeout: float | None = None) -> dict[str, Any]:
        return self.call("help", timeout=timeout)

    def eval(self, source: str | bytes, timeout: float | None = None) -> dict[str, Any]:
        return self.call("eval", source, timeout=timeout)

    def tasks(self, timeout: float | None = None) -> dict[str, Any]:
        return self.call("tasks", timeout=timeout)

    task_list = tasks

    def task_kill(self, target: str, timeout: float | None = None) -> dict[str, Any]:
        return self.call("task_kill", target, timeout=timeout)

    def windows(self, timeout: float | None = None) -> dict[str, Any]:
        return self.call("windows", timeout=timeout)

    def focus(self, target: str | None = None, timeout: float | None = None) -> dict[str, Any]:
        return self.call("focus", target or b"", timeout=timeout)

    def window_focus(
        self, target: str | None = None, timeout: float | None = None
    ) -> dict[str, Any]:
        return self.call("window_focus", target or b"", timeout=timeout)

    def text(self, which: str = "focus", timeout: float | None = None) -> Any:
        mode = b"all" if which == "all" else b"focus"
        return self.call("text", mode, timeout=timeout)

    def mouse(
        self,
        x: int | None = None,
        y: int | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        payload = b"" if x is None or y is None else f"{int(x)},{int(y)}".encode()
        return self.call("mouse", payload, timeout=timeout)

    def mode(self, name: str, timeout: float | None = None) -> dict[str, Any]:
        return self.call("mode", name, timeout=timeout)

    def clip_get(self, timeout: float | None = None) -> dict[str, Any]:
        return self.call("clip_get", timeout=timeout)

    def clip_set(self, text: str | bytes, timeout: float | None = None) -> dict[str, Any]:
        return self.call("clip_set", text, timeout=timeout)

    def ls(self, path: str = "/", timeout: float | None = None) -> list[dict[str, Any]]:
        return self.call("ls", path, timeout=timeout)

    def list_dir(self, path: str = "/", timeout: float | None = None) -> list[dict[str, Any]]:
        return self.call("list", path, timeout=timeout)

    def stat(self, path: str, timeout: float | None = None) -> dict[str, Any]:
        return self.call("stat", path, timeout=timeout)

    def doc_read(self, path: str = "", timeout: float | None = None) -> dict[str, Any]:
        return self.call("doc_read", path, timeout=timeout)

    def doc_write(
        self, path: str, content: str | bytes, timeout: float | None = None
    ) -> dict[str, Any]:
        if isinstance(content, str):
            content = content.encode("utf-8")
        return self.call("doc_write", path.encode("utf-8") + b"\0" + content, timeout=timeout)

    def toast(self, text: str, timeout: float | None = None) -> dict[str, Any]:
        return self.call("toast", text, timeout=timeout)

    def guards(self, what: str = "", timeout: float | None = None) -> dict[str, Any]:
        return self.call("guards", what, timeout=timeout)

    def sysinfo(self, timeout: float | None = None) -> dict[str, Any]:
        return self.call("sysinfo", timeout=timeout)

    def pull(self, path: str, timeout: float | None = None) -> bytes:
        status, data = self.request("pull", path, timeout=timeout)
        if status != "ok":
            raise HermesRemoteError("pull", data.decode("utf-8", "replace").strip())
        return data

    def push(
        self, path: str, data: bytes | str, timeout: float | None = None
    ) -> dict[str, Any]:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return self.call("push", path.encode("utf-8") + b"\0" + data, timeout=timeout)

    def events_drain(self, timeout: float | None = None) -> list[dict[str, Any]]:
        return self.call("events", timeout=timeout)

    def idle(self, timeout: float | None = None) -> dict[str, Any]:
        return self.call("idle", timeout=timeout)

    def take_events(self) -> list[dict[str, Any]]:
        """Return and clear asynchronous ``HEVT`` records seen so far."""
        out = [event.as_dict() for event in self.events]
        self.events.clear()
        return out


def _main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Talk to the Hermes COM1 daemon")
    parser.add_argument("socket", help="QEMU COM1 unix socket")
    parser.add_argument("op", help="operation name")
    parser.add_argument("payload", nargs="?", default="", help="raw payload text")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--beacon", action="store_true", help="wait for HBEACON first")
    args = parser.parse_args(list(argv) if argv is not None else None)

    client = HermesDaemonClient(args.socket, timeout=args.timeout)
    try:
        if args.beacon:
            print(json.dumps({"beacon": client.wait_beacon(args.timeout)}))
        if args.op == "pull":
            sys.stdout.buffer.write(client.pull(args.payload, timeout=args.timeout))
        else:
            print(json.dumps(client.call(args.op, args.payload, timeout=args.timeout),
                             indent=2, sort_keys=True))
    finally:
        client.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
