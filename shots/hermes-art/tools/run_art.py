#!/usr/bin/env python3
"""Boot stock TinkerOS live CD under QEMU TCG, stage Hermes/Art on a FAT32
overlay, then GRRead+GrBlot wallpaper/icon/splash with QMP screenshots."""
from __future__ import annotations
import json, sys, time, importlib.util
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from artqemu import QMP, start_vm, stop_vm, ROOT, SHOTS

ISO = Path(sys.argv[1]) if len(sys.argv) > 1 else (ROOT / "Extras" / "TempleOS.ISO")
LABEL = sys.argv[2] if len(sys.argv) > 2 else "run"
DISK = SHOTS / "raw" / "hermes-art-overlay.img"
OUT = SHOTS
RAW = OUT / "raw" / LABEL
FRAMES = RAW / "frames"
RESULT_JSON = RAW / "run-meta.json"

spec = importlib.util.spec_from_file_location("fat32_read", ROOT / "scripts" / "fat32_read.py")
fat32_read = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fat32_read)


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S") + " " + msg, flush=True)


def guest_result(name: str) -> str | None:
    try:
        fs = fat32_read.open_first_fat(DISK)
        try:
            return fs.read_file(f"/Tmp/{name}").decode("latin1", "replace")
        finally:
            fs.close()
    except Exception:
        return None


def main() -> int:
    FRAMES.mkdir(parents=True, exist_ok=True)
    for p in FRAMES.glob("*.png"):
        p.unlink()
    meta = start_vm("hermes-art", ISO, disks=[(DISK, "raw")])
    log(f"qemu pid {meta['pid']}")
    time.sleep(1)
    qmp = QMP(Path(meta["qmp"]), timeout=120)
    result: dict = {"iso": ISO.name, "iso_path": str(ISO), "label": LABEL, "disk": DISK.name, "frames": [], "guest": {}, "errors": []}
    try:
        log("booting live CD")
        time.sleep(14)
        qmp.type_text("n\n", delay=0.15)
        time.sleep(3)
        qmp.type_text("n\n", delay=0.15)
        time.sleep(4)
        qmp.type_text("AutoComplete(OFF);\n", delay=0.06)
        time.sleep(2)
        qmp.type_text("MountIDEAuto;\n", delay=0.08)
        time.sleep(5)
        qmp.type_text('Dir("C:/");\n', delay=0.06)
        time.sleep(3)
        qmp.screendump(RAW / "00-overlay-listed.png")
        log("stage + verify")
        qmp.type_text('#include "C:/RUN.HC";\n', delay=0.05)

        deadline = time.time() + 300
        n = 0
        done = None
        while time.time() < deadline:
            n += 1
            dest = FRAMES / f"frame-{n:04d}.png"
            qmp.screendump(dest)
            result["frames"].append(dest.name)
            if n % 10 == 0:
                log(f"frame {n}")
            if n % 4 == 0:
                for cand in ("R_ALL_OK", "R_FAIL"):
                    val = guest_result(cand)
                    if val is not None:
                        done = cand
                        break
            if done:
                break
            time.sleep(0.25)
        time.sleep(1)
        qmp.screendump(RAW / "99-final.png")
        result["done_marker"] = done
        for cand in ("R_WALLPAPER_OK", "R_WALLPAPER_NULL", "R_ICON_OK", "R_ICON_NULL",
                     "R_SPLASH_OK", "R_SPLASH_NULL", "R_ALL_OK", "R_FAIL",
                     "HERMES_ART_STAGED"):
            val = guest_result(cand)
            if val is not None:
                result["guest"][cand] = val
        log("guest results: " + json.dumps(result["guest"]))
        result["ok"] = done == "R_ALL_OK"
    except Exception as e:
        result["ok"] = False
        result["errors"].append(f"{type(e).__name__}: {e}")
        log(f"ERROR {e}")
        try:
            qmp.screendump(RAW / "99-error.png")
        except Exception:
            pass
    finally:
        RESULT_JSON.write_text(json.dumps(result, indent=2))
        try:
            qmp.quit()
            time.sleep(1)
        except Exception:
            pass
        stop_vm(meta)
        qmp.close()
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
