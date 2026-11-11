#!/usr/bin/env python3
"""Capture B5 guest-tools RPC evidence from a fully booted TOH guest.

Saves shots/hermes-tools/{20-toast,21-windows,22-guards,23-sysinfo}.png
plus the RPC JSON in shots/hermes-tools/tools.json.  Bounded waits only.
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
OUT = ROOT / "shots" / "hermes-tools"
DISK = RUN / "hermes-tools-shots.qcow2"


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
        rec["text"] = text[:500]
    except Exception as e:
        rec["text"] = f"<ocr {type(e).__name__}>"
    log(f"shot {name} {rec['size']} colors={rec['unique_colors']} bbox={rec['bbox']}")
    return rec


def main() -> int:
    if not ISO.is_file():
        log(f"missing {ISO}")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    if DISK.exists():
        DISK.unlink()
    subprocess.check_call(["qemu-img", "create", "-f", "qcow2", str(DISK), "2G"])
    meta = start_vm("hermes-tools-shots", ISO, DISK, memory="2G", boot="d")
    time.sleep(1)
    qmp = QMP(Path(meta["qmp"]), timeout=60)
    cli = HermesDaemonClient(str(meta["com1"]), timeout=60)
    stop = False

    def drain() -> None:
        while not stop:
            try:
                cli.drain(0.1)
            except Exception:
                return

    thread = threading.Thread(target=drain, daemon=True)
    thread.start()
    result: dict = {"shots": {}, "rpc": {}}
    try:
        time.sleep(35)
        stop = True
        thread.join(timeout=1)
        for _ in range(6):
            try:
                result["rpc"]["ping"] = cli.ping(timeout=20)
                break
            except Exception as e:
                result["rpc"]["ping_error"] = f"{type(e).__name__}: {e}"
                time.sleep(4)
        result["rpc"]["toast"] = cli.toast("B5 toast: guest tools are live", timeout=20)
        time.sleep(1)
        result["shots"]["20-tools-toast"] = shot(qmp, "20-tools-toast")

        result["rpc"]["windows"] = cli.windows(timeout=20)
        result["rpc"]["toast_windows"] = cli.toast("B5 windows: see tools.json", timeout=20)
        time.sleep(1)
        result["shots"]["21-tools-windows"] = shot(qmp, "21-tools-windows")

        result["rpc"]["mode_agent"] = cli.mode("agent", timeout=20)
        result["rpc"]["guards"] = cli.guards("Fmt", timeout=20)
        blocked = (result["rpc"]["guards"] or {}).get("blocked") or []
        result["rpc"]["toast_guards"] = cli.toast(
            "B5 guards: Fmt allow=0 blocked=%d" % len(blocked), timeout=20
        )
        time.sleep(1)
        result["shots"]["22-tools-guards"] = shot(qmp, "22-tools-guards")

        result["rpc"]["sysinfo"] = cli.sysinfo(timeout=20)
        info = result["rpc"]["sysinfo"] or {}
        result["rpc"]["toast_sysinfo"] = cli.toast(
            "B5 sysinfo: version=%s mode=%s"
            % (info.get("version", "?"), info.get("mode", "?")),
            timeout=20,
        )
        time.sleep(1)
        result["shots"]["23-tools-sysinfo"] = shot(qmp, "23-tools-sysinfo")
        result["rpc"]["mode_user"] = cli.mode("user", timeout=20)
        result["rpc"]["events"] = cli.take_events()[-10:]
    finally:
        stop = True
        try:
            cli.close()
        except Exception:
            pass
        try:
            stop_vm(meta, qmp)
        except Exception:
            pass
        qmp.close()
    (OUT / "tools.json").write_text(json.dumps(result, indent=2))
    ok = all(v.get("unique_colors", 0) >= 2 for v in result["shots"].values())
    log(f"tools palette/nonblank check: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
