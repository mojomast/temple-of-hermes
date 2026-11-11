#!/usr/bin/env python3
"""COM1 handshake through the hermes-templeos plugin's own QEMU/serial path.

Boots the accepted Temple of Hermes ISO with the plugin's build_argv/SerialPort
code, waits for the guest HBEACON on COM1, then sends one HRPC ping request and
records the HRPL reply. No secrets, tokens, host names, or network are used.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ISO = ROOT / "dist" / "TempleOfHermes-0.1.2.ISO"
PLUGIN = Path(os.environ.get("TOH_PLUGIN_ROOT", ROOT / "run" / "hermes-templeos"))
OUT = ROOT / "shots" / "hermes-iso-0.1.2"
LOG = OUT / "com1-handshake.log"
RESULT = OUT / "com1-handshake.json"

if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))

from templeos.envsafe import child_env  # noqa: E402
from templeos.qemu import build_argv, create_disk, spawn, terminate  # noqa: E402
from templeos.qmp import QMPClient  # noqa: E402
from templeos.serial import SerialPort  # noqa: E402
from templeos import screen as plugin_screen  # noqa: E402


def log(msg: str) -> None:
    line = (time.strftime("%H:%M:%S ") + msg).rstrip()
    print(line, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def read_exact(port: SerialPort, n: int, timeout_s: float = 10.0) -> bytes:
    deadline = time.monotonic() + timeout_s
    buf = b""
    while len(buf) < n and time.monotonic() < deadline:
        chunk = port.read(n - len(buf), timeout_s=0.2)
        if chunk:
            buf += chunk
    if len(buf) < n:
        raise TimeoutError(f"short serial read: {len(buf)}/{n}")
    return buf


def main() -> int:
    if not ISO.is_file():
        print(f"missing {ISO}")
        return 2
    if not (PLUGIN / "templeos" / "qemu.py").is_file():
        print(f"missing plugin tree {PLUGIN}")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    run = ROOT / "run" / "com1-plugin"
    run.mkdir(parents=True, exist_ok=True)
    for name in ("qmp.sock", "vnc.sock", "com1.sock"):
        (run / name).unlink(missing_ok=True)
    disk = run / "templeos.qcow2"
    if not disk.is_file():
        create_disk(disk)
    argv = build_argv(
        flavor="tinkeros",
        iso=ISO,
        disk=disk,
        qmp=run / "qmp.sock",
        vnc=run / "vnc.sock",
        com1=run / "com1.sock",
        accel="tcg",
        name="toh-com1-handshake",
    )
    log("plugin QEMU argv built (TCG, -nic none, COM1 unix socket)")
    proc = spawn(argv, env=child_env(), cwd=run, log_path=run / "qemu.log")
    qmp = QMPClient()
    port = SerialPort()
    result = {
        "plugin_commit": "b15c396c308b638c00959740dfa3d28920f45484",
        "iso": ISO.name,
        "beacon": None,
        "hrpc_request": None,
        "hrpc_reply": None,
        "ok": False,
    }
    try:
        qmp.connect(run / "qmp.sock", timeout_s=30.0)
        port.open(run / "com1.sock", timeout_s=10.0)
        plugin_screen.bind(qmp=qmp, serial=port, flavor="tinkeros", state_dir=run)
        log("plugin COM1 open; waiting for guest HBEACON through plugin screen/read_text")
        beacon = ""
        deadline = time.monotonic() + 90.0
        while time.monotonic() < deadline:
            body = plugin_screen.read_text()
            text = str(body.get("text") or "")
            if "HBEACON " in text:
                beacon = text[text.index("HBEACON "):].splitlines()[0].strip()
                result["screen_source"] = body.get("source")
                break
            time.sleep(0.5)
        if not beacon:
            raise TimeoutError("plugin read_text did not receive HBEACON")
        result["beacon"] = beacon
        log("beacon via plugin read_text (" + str(result.get("screen_source")) + "): " + beacon)
        time.sleep(0.5)
        port.read_available()
        request = "HREQ 1 ping 0\n"
        result["hrpc_request"] = request.strip()
        port.write(request.encode("ascii"))
        head = port.read_until(b"HRPL ", timeout_s=15.0)
        line = port.read_until(b"\n", timeout_s=10.0)
        header = (head + line).decode("ascii", "replace")
        header = header[header.index("HRPL "):].strip()
        parts = header.split()
        length = int(parts[3])
        payload = read_exact(port, length)
        reply_text = payload.decode("utf-8", "replace")
        result["hrpc_reply"] = {"header": header, "payload": reply_text}
        log("hrpc reply: " + header + " " + reply_text)
        result["ok"] = parts[0] == "HRPL" and parts[2] == "ok"
        try:
            qmp.command_timeout_s = 5.0
            qmp.cmd("quit", timeout_s=5.0)
        except Exception:
            pass
    finally:
        try:
            plugin_screen.unbind()
        except Exception:
            pass
        port.close()
        qmp.close()
        terminate(proc, timeout_s=5.0)
        RESULT.write_text(json.dumps(result, indent=2) + "\n")
        log("handshake ok=" + str(result["ok"]))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
