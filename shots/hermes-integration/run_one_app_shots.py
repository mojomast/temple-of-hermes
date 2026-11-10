#!/usr/bin/env python3
"""Capture selected app windows with one fresh boot per app."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from qemu_hermes import QMP, RUN, glyph_text, start_vm, stop_vm  # noqa: E402

ISO = ROOT / "dist" / "TempleOfHermes-0.1.0.ISO"
OUT = ROOT / "shots" / "hermes-integration"
APPS = [
    ("Codex", "12-codex"),
    ("Psyche", "13-psyche"),
    ("Capybara", "14-capybara"),
    ("MessengerRun", "15-messenger-run"),
    ("HermesBBS", "16-hermes-bbs"),
    ("Dojo", "18-dojo"),
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
    log(f"shot {name} colors={rec['unique_colors']} bbox={rec['bbox']}")
    return rec


def run_one(app: str, name: str) -> dict:
    disk = RUN / f"one-{app}.qcow2"
    if disk.exists():
        disk.unlink()
    subprocess.check_call(["qemu-img", "create", "-f", "qcow2", str(disk), "2G"])
    meta = start_vm(f"one-{app}", ISO, disk, memory="2G", boot="d")
    time.sleep(1)
    qmp = QMP(Path(meta["qmp"]), timeout=60)
    try:
        time.sleep(35)
        qmp.send_qcodes("esc", hold=100)
        time.sleep(4)
        qmp.type_text(f'Cd("::/Hermes/Apps/{app}");\n', delay=0.12)
        time.sleep(1)
        qmp.type_text('#include "Run.HC";\n', delay=0.12)
        time.sleep(35)
        return shot(qmp, name)
    finally:
        try:
            stop_vm(meta, qmp)
        except Exception:
            pass
        qmp.close()


def main() -> int:
    result = {"apps": {}}
    for app, name in APPS:
        log(f"boot {app}")
        try:
            result["apps"][app] = run_one(app, name)
        except Exception as e:
            result["apps"][app] = {"error": f"{type(e).__name__}: {e}"}
    (OUT / "one-apps.json").write_text(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
