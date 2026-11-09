#!/usr/bin/env python3
"""Host client for the Temple of Hermes COM1 protocol (HBEACON/HREQ/HRPL/HEVT)."""
from __future__ import annotations

import socket
import time
from pathlib import Path


class Hrpc:
    def __init__(self, path: Path, timeout: float = 60.0, log: Path | None = None):
        self.path = path
        self.timeout = timeout
        self.log_path = log
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            try:
                self.sock.connect(str(path))
                break
            except OSError as e:
                last = e
                time.sleep(0.1)
        else:
            raise RuntimeError(f"HRPC connect failed: {path}: {last}")
        self.buf = b""
        self.next_id = 1
        self.events: list[str] = []
        self.beacons: list[str] = []
        self.transcript = bytearray()

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def _log(self, direction: str, data: bytes) -> None:
        self.transcript.extend(f"\n{direction} ".encode() + data)
        if self.log_path:
            with self.log_path.open("ab") as f:
                f.write(f"\n{direction} ".encode() + data)

    def _recv_some(self, timeout: float) -> bytes:
        self.sock.settimeout(timeout)
        try:
            chunk = self.sock.recv(65536)
        except socket.timeout:
            return b""
        if chunk:
            self._log("<<", chunk)
        return chunk or b""

    def drain(self, seconds: float = 0.4) -> None:
        deadline = time.time() + seconds
        while time.time() < deadline:
            chunk = self._recv_some(0.15)
            if chunk:
                self.buf += chunk
            self._consume_async()

    def wait_beacon(self, timeout: float = 300.0) -> str:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.beacons:
                return self.beacons[-1]
            chunk = self._recv_some(min(1.0, max(0.05, deadline - time.time())))
            if chunk:
                self.buf += chunk
            self._consume_async()
        raise TimeoutError(f"no HBEACON in {timeout}s, buf={self.buf[-400]!r}")

    def _consume_async(self) -> None:
        while True:
            if self.buf.startswith(b"\r"):
                self.buf = self.buf[1:]
                continue
            # Find a known header at a line start
            for prefix in (b"HBEACON ", b"HEVT ", b"HRPL "):
                i = self.buf.find(prefix)
                if i == -1:
                    continue
                if i > 0:
                    # discard leading garbage
                    self.buf = self.buf[i:]
                break
            else:
                return
            if self.buf.startswith(b"HBEACON "):
                if b"\n" not in self.buf:
                    return
                line, self.buf = self.buf.split(b"\n", 1)
                self.beacons.append(line.decode("ascii", "replace").strip())
                continue
            if self.buf.startswith(b"HEVT ") or self.buf.startswith(b"HRPL "):
                if b"\n" not in self.buf:
                    return
                line, rest = self.buf.split(b"\n", 1)
                parts = line.decode("ascii", "replace").split()
                if len(parts) < 4:
                    self.buf = rest
                    continue
                try:
                    length = int(parts[3])
                except ValueError:
                    self.buf = rest
                    continue
                if len(rest) < length:
                    return
                payload, self.buf = rest[:length], rest[length:]
                rec = line.decode("ascii", "replace") + "\n" + payload.decode("utf-8", "replace")
                if parts[0] == "HEVT":
                    self.events.append(rec)
                else:
                    self._pending_rpl = rec
                    self._pending_payload = payload
                    self._pending_status = parts[2]
                continue
            return

    def request(self, op: str, payload: bytes = b"", timeout: float = 60.0) -> tuple[str, bytes]:
        req_id = self.next_id
        self.next_id += 1
        header = f"HREQ {req_id} {op} {len(payload)}\n".encode("ascii")
        self._log(">>", header + payload)
        self.sock.sendall(header + payload)
        self._pending_rpl = None
        self._pending_payload = None
        self._pending_status = None
        deadline = time.time() + timeout
        while time.time() < deadline:
            chunk = self._recv_some(min(1.0, max(0.05, deadline - time.time())))
            if chunk:
                self.buf += chunk
            self._consume_async()
            if self._pending_rpl is not None:
                status = self._pending_status or "ok"
                data = self._pending_payload or b""
                self._pending_rpl = None
                return status, data
        raise TimeoutError(f"no HRPL for {op} id={req_id}, buf={self.buf[-400]!r}")

    def text(self) -> str:
        return self.transcript.decode("utf-8", "replace")
