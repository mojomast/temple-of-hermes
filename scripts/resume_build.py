#!/usr/bin/env python3
"""Resume the ISO build after the stock TinkerOS install has started copying.

Attaches to the already-running hermes-build QEMU, waits for 'Reboot Now',
declines the reboot, serial-pushes the overlay, and runs MakeDistro.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_iso import (  # noqa: E402
    DISK,
    DIST,
    ISO_NAME,
    LOG,
    RECEIVER,
    SERIAL_LOG,
    SHOT,
    overlay_files,
    send_overlay,
    shot,
)
from fat32_read import extract, open_first_fat  # noqa: E402
from qemu_hermes import QMP, RUN, Serial, stop_vm, wait_for_text  # noqa: E402


def log(msg: str) -> None:
    line = time.strftime("%H:%M:%S") + " " + msg
    print(line, flush=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def main() -> int:
    qmp_path = RUN / "hermes-build" / "qmp.sock"
    com_path = RUN / "hermes-build" / "com1.sock"
    pid = int((RUN / "hermes-build" / "pid").read_text().strip())
    meta = {"pid": pid}
    qmp = QMP(qmp_path, timeout=30)
    ser = Serial(com_path, timeout=30, log=SERIAL_LOG)
    try:
        shot(qmp, "20-resume")
        log("waiting for Reboot Now (install copy in progress)")
        wait_for_text(
            qmp, SHOT, "Reboot Now", timeout=2400, interval=12, prefix="rebootwait"
        )
        shot(qmp, "21-reboot-now")
        qmp.type_text("n\n")
        time.sleep(2)
        qmp.send_qcodes("shift", "esc")
        time.sleep(0.4)
        qmp.send_qcodes("shift", "esc")
        time.sleep(0.6)
        qmp.type_text("\n")
        shot(qmp, "22-after-install")
        log("typing serial receiver")
        qmp.type_text(RECEIVER, delay=0.07)
        time.sleep(2)
        shot(qmp, "23-receiver")
        send_overlay(ser, overlay_files())
        time.sleep(1)
        qmp.send_qcodes("shift", "esc")
        time.sleep(0.3)
        qmp.type_text('\n#include "C:/Tmp/AfterOverlay.HC";\n', delay=0.07)
        time.sleep(2)
        shot(qmp, "24-after-overlay")
        log("starting MakeDistro (BootDVDIns + RedSeaISO), very slow under TCG")
        qmp.type_text('C:;\nCd("/");\n#include "C:/Adam/Hermes/MakeDistro";\n', delay=0.07)
        wait_for_text(
            qmp, SHOT, "ISO written", timeout=5400, interval=20, prefix="distro"
        )
        shot(qmp, "25-iso-written")
        time.sleep(2)
    finally:
        log("stopping VM")
        try:
            shot(qmp, "99-final")
        except Exception:
            pass
        ser.close()
        stop_vm(meta, qmp)
        qmp.close()

    raw = RUN / "hermes-build.raw"
    log(f"converting {DISK} -> {raw}")
    if raw.exists():
        raw.unlink()
    subprocess.check_call(["qemu-img", "convert", "-O", "raw", str(DISK), str(raw)])
    try:
        fs = open_first_fat(raw)
        listing = "\n".join(fs.tree())
        (RUN / "fat-tree.txt").write_text(listing)
        log("fat tree (head):\n" + "\n".join(listing.splitlines()[:80]))
        fs.close()
    except Exception as e:
        log(f"fat tree failed: {e}")

    dest = DIST / ISO_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_err = None
    for cand in (
        "/Tmp/TempleOfHermes.ISO.C",
        "/Tmp/TempleOfHermes.ISO.C.Z",
        "/Tmp/TempleOfHermes.ISO",
    ):
        try:
            extract(raw, cand, dest)
            log(f"extracted {cand} -> {dest} ({dest.stat().st_size} bytes)")
            last_err = None
            break
        except Exception as e:
            last_err = e
            log(f"extract {cand} failed: {e}")
    if last_err and not dest.exists():
        raise last_err
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    (DIST / "SHA256SUMS").write_text(f"{digest}  {ISO_NAME}\n")
    log(f"SHA256 {digest}")
    raw.unlink(missing_ok=True)
    log("resume build finished")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"RESUME FAILED: {type(e).__name__}: {e}")
        raise
