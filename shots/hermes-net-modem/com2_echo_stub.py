#!/usr/bin/env python3
"""Local COM2 echo/loopback stub for the Modem / Net acceptance test.

This is a sandbox-only peer.  It attaches to the QEMU serial unix socket used
as COM2, speaks the Hermes Hayes-style AT protocol, and uses the in-memory
LoopbackTransport so every payload is echoed back without touching a real
BBS, a VPS, DNS, or any network.

Usage:
    python3 com2_echo_stub.py SOCKET LOG [--timeout SECONDS] [--allow DEST]

The default allow-list is exactly ("hermes",).  Payload bytes are logged here
because this is a local test fixture; the production host modem deliberately
logs only command text and byte counts.
"""
from __future__ import annotations

import argparse
import importlib.util
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEM_PATH = ROOT / "host" / "hermes_modem.py"


def load_modem_module():
    spec = importlib.util.spec_from_file_location("hermes_modem", MODEM_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODEM_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def log_line(log, text: str) -> None:
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    line = f"{stamp} {text}"
    print(line, flush=True)
    log.write(line + "\n")
    log.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("socket", type=Path)
    parser.add_argument("log", type=Path)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--allow", action="append", default=[], metavar="DEST")
    args = parser.parse_args(argv)

    allow = args.allow or ["hermes"]
    modem_module = load_modem_module()
    modem = modem_module.HermesModem(
        enabled=True,
        allow_list=allow,
        transport=modem_module.LoopbackTransport(),
        log_path=args.log.with_suffix(".at.log"),
    )

    args.log.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + args.timeout
    with args.log.open("a", encoding="utf-8") as log:
        log_line(log, f"stub start socket={args.socket.name} allow={allow} transport=loopback")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(min(30.0, max(1.0, args.timeout)))
        try:
            sock.connect(str(args.socket))
        except OSError as exc:
            log_line(log, f"stub connect failed: {type(exc).__name__}: {exc}")
            return 2
        log_line(log, "stub connected to QEMU COM2")
        sock.settimeout(0.5)
        total_in = 0
        total_out = 0
        try:
            while time.time() < deadline:
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    continue
                if not chunk:
                    log_line(log, "stub saw EOF")
                    break
                total_in += len(chunk)
                log_line(log, f"guest->stub {len(chunk)} bytes: {chunk!r}")
                reply = modem.feed(chunk)
                if reply:
                    sock.sendall(reply)
                    total_out += len(reply)
                    log_line(log, f"stub->guest {len(reply)} bytes: {reply!r}")
        except OSError as exc:
            log_line(log, f"stub socket error: {type(exc).__name__}: {exc}")
        finally:
            try:
                sock.close()
            except OSError:
                pass
            log_line(log, f"stub stop guest_bytes={total_in} stub_bytes={total_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
