#!/usr/bin/env python3
"""Capture one window shot per accepted app by typing its Run.HC in the guest.

The launcher is closed first; each app is included from its own directory, so
this does not depend on the daemon eval context.  QEMU waits are bounded.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "host"))

from qemu_hermes import QMP, RUN, glyph_text, start_vm, stop_vm  # noqa: E402
from hermes_daemon_client import HermesDaemonClient  # noqa: E402

ISO = ROOT / "dist" / "TempleOfHermes-0.1.0.ISO"
OUT = ROOT / "shots" / "hermes-integration"
DISK = RUN / "hermes-apps-shots.qcow2"

APPS = [
    ("HermesChat", "Hermes Chat", "10-hermes-chat"),
    ("WorldSim", "WorldSim", "11-worldsim"),
    ("Codex", "Codex of Nous", "12-codex"),
    ("Psyche", "Psyche", "13-psyche"),
    ("Capybara", "Capybara", "14-capybara"),
    ("MessengerRun", "Messenger Run", "15-messenger-run"),
    ("HermesBBS", "Hermes BBS", "16-hermes-bbs"),
    ("Threshold", "The Threshold", "17-threshold"),
    ("Dojo", "Dojo", "18-dojo"),
    ("Offerings", "Offerings", "19-offerings"),
]


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S") + " " + msg, flush=True)


def shot(qmp: QMP, name: str) -> dict:
    dest = OUT / f"{name}.png"
    qmp.screendump(dest)
    im = Image.open(dest).convert("RGB")
    colors = sorted(set(im.getdata()))
    rec = {
        "path": str(dest.relative_to(ROOT)),
        "size": list(im.size),
        "unique_colors": len(colors),
        "bbox": list(im.convert("L").getbbox() or (0, 0, 0, 0)),
    }
    try:
        text = glyph_text(dest)
        (OUT / f"{name}.txt").write_text(text)
        rec["text"] = text[:800]
    except Exception as e:
        rec["text"] = f"<ocr {type(e).__name__}>"
    log(f"shot {name} {rec['size']} colors={rec['unique_colors']} bbox={rec['bbox']}")
    return rec


def main() -> int:
    if not ISO.is_file():
        log(f"missing {ISO}")
        return 2
    if DISK.exists():
        DISK.unlink()
    subprocess.check_call(["qemu-img", "create", "-f", "qcow2", str(DISK), "2G"])
    rundir = RUN / "hermes-apps-shots"
    rundir.mkdir(parents=True, exist_ok=True)
    com2 = rundir / "com2.sock"
    com2.unlink(missing_ok=True)
    meta = start_vm(
        "hermes-apps-shots", ISO, DISK, memory="2G", boot="d",
        extra=["-serial", f"unix:{com2},server=on,wait=off"],
    )
    log(f"qemu pid {meta['pid']}")
    time.sleep(1)
    qmp = QMP(Path(meta["qmp"]), timeout=60)
    cli = HermesDaemonClient(str(meta["com1"]), timeout=60)
    relay = subprocess.Popen(
        [sys.executable, str(ROOT / "host" / "hermes_chat_relay.py"),
         "--enable", "--allow", "hermes", "--connect", str(com2)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    stop = False

    def drain() -> None:
        while not stop:
            try:
                cli.drain(0.1)
            except Exception:
                return

    thread = threading.Thread(target=drain, daemon=True)
    thread.start()
    result: dict = {"apps": {}}
    try:
        time.sleep(35)
        stop = True
        thread.join(timeout=1)
        qmp.send_qcodes("esc", hold=100)
        time.sleep(4)
        for app, title, name in APPS:
            log(f"launch {app}")
            qmp.type_text(f'Cd("::/Hermes/Apps/{app}");\n', delay=0.12)
            time.sleep(1)
            qmp.type_text('#include "Run.HC";\n', delay=0.12)
            time.sleep(22)
            result["apps"][app] = shot(qmp, name)
            try:
                cli.call("task_kill", title, timeout=20)
            except Exception:
                pass
            qmp.send_qcodes("esc", hold=100)
            time.sleep(4)
    finally:
        stop = True
        try:
            cli.close()
        except Exception:
            pass
        relay.terminate()
        try:
            relay.wait(timeout=5)
        except Exception:
            relay.kill()
        try:
            stop_vm(meta, qmp)
        except Exception:
            pass
        qmp.close()
    (OUT / "apps.json").write_text(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
