#!/usr/bin/env python3
"""COM2 <-> TLS relay built on the repository's host/hermes_modem.py.

The modem is enabled with the single allow-list destination ``bbs``.  It logs
commands, byte counts, and denials only; AUTH payloads and token values are
never written to the log.
"""
from __future__ import annotations

import argparse
import importlib.util
import socket
import ssl
import sys
import time
from pathlib import Path


class TlsTransport:
    def __init__(self, port: int) -> None:
        self.port = int(port)
        self.sock = None
        self.tls = None

    def connect(self, destination: str) -> None:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        raw = socket.create_connection(("localhost", self.port), timeout=5.0)
        self.sock = raw
        self.tls = ctx.wrap_socket(raw, server_hostname="localhost")
        self.tls.setblocking(False)

    def send(self, data: bytes) -> int:
        if self.tls is None:
            raise OSError("not connected")
        view = memoryview(data)
        sent = 0
        while sent < len(view):
            try:
                n = self.tls.send(view[sent:])
            except (BlockingIOError, ssl.SSLWantWriteError):
                time.sleep(0.005)
                continue
            if n <= 0:
                break
            sent += n
        return sent

    def recv(self, max_bytes: int, timeout: float | None = None) -> bytes:
        if self.tls is None or max_bytes <= 0:
            return b""
        try:
            return self.tls.recv(max_bytes)
        except (BlockingIOError, ssl.SSLWantReadError):
            return b""

    def disconnect(self) -> None:
        for sock in (self.tls, self.sock):
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        self.tls = None
        self.sock = None


def load_modem(host_repo: Path):
    path = host_repo / "host" / "hermes_modem.py"
    spec = importlib.util.spec_from_file_location("hermes_modem", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.HermesModem


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", required=True)
    ap.add_argument("--tls-port", required=True, type=int)
    ap.add_argument("--log", required=True)
    ap.add_argument("--modem-repo", required=True)
    args = ap.parse_args()

    HermesModem = load_modem(Path(args.modem_repo))
    modem = HermesModem(
        enabled=True,
        allow_list=("bbs",),
        transport=TlsTransport(args.tls_port),
        log_path=args.log,
    )
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    deadline = time.time() + 20
    while True:
        try:
            sock.connect(args.serial)
            break
        except OSError:
            if time.time() >= deadline:
                raise
            time.sleep(0.1)
    sock.settimeout(0.2)
    try:
        while True:
            try:
                data = sock.recv(4096)
            except socket.timeout:
                continue
            if not data:
                break
            reply = modem.feed(data)
            if reply:
                sock.sendall(reply)
    finally:
        modem.reset()
        sock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
