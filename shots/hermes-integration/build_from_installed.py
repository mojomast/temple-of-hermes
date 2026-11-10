#!/usr/bin/env python3
"""Build the integration ISO from the already-installed C: disk.

Boots the public live CD plus the installed disk and a FAT32 overlay disk,
answers NO to install and tour, copies the Hermes overlay onto C:, then runs
the in-guest Adam/Hermes/MakeDistro.HC path.  All waits are bounded.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "shots" / "hermes-integration"))

import build_iso  # noqa: E402
import make_overlay_fat32  # noqa: E402
from qemu_hermes import QMP, RUN, STOCK_ISO, glyph_text, start_vm, stop_vm  # noqa: E402

from build_integration_iso import hermes_overlay  # noqa: E402
from fat32_read import extract, open_first_fat  # noqa: E402

DISK = RUN / "hermes-build.qcow2"
OVERLAY = RUN / "hermes-overlay.img"
ISO_OUT = ROOT / "dist" / "TempleOfHermes-0.1.1.ISO"
LOG = RUN / "integration-build2.log"


def log(msg: str) -> None:
    line = time.strftime("%H:%M:%S") + " " + msg
    print(line, flush=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def screen(qmp: QMP, name: str) -> str:
    dest = RUN / "hermes-build2" / f"{name}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    qmp.screendump(dest)
    try:
        return glyph_text(dest)
    except Exception as e:
        return f"<ocr {type(e).__name__}>"


def wait_for(qmp: QMP, needle: str, timeout: float = 180.0, prefix: str = "w") -> str:
    deadline = time.time() + timeout
    n = 0
    last = ""
    while time.time() < deadline:
        n += 1
        last = screen(qmp, f"{prefix}-{n:03d}")
        if needle.lower() in last.lower():
            log(f"found {needle!r} after {n} reads")
            return last
        time.sleep(4)
    raise TimeoutError(f"timeout waiting for {needle!r}; last={last[-300:]!r}")


def type_slow(qmp: QMP, text: str, delay: float = 0.14) -> None:
    qmp.type_text(text, delay=delay)


def mount_drive(qmp: QMP, letter: str, dev: str) -> None:
    """Mount one ATA hard drive through the interactive Mount() wizard."""
    type_slow(qmp, "Mount(FALSE,TRUE);\n")
    time.sleep(3)
    type_slow(qmp, letter + "\n")
    time.sleep(2)
    type_slow(qmp, "\n")
    time.sleep(2)
    type_slow(qmp, "s\n")
    time.sleep(2)
    type_slow(qmp, dev + "\n")
    time.sleep(2)
    type_slow(qmp, "\n")
    time.sleep(2)
    type_slow(qmp, "\n")
    time.sleep(3)
    log(f"mounted {letter}: dev {dev}")


def make_run_hc_all(items: list[tuple[str, bytes]], src_drv: str = "D") -> bytes:
    """Copy every overlay item, creating each destination directory first."""
    dirs: set[str] = set()
    for dest, _ in items:
        parent = dest.rsplit("/", 1)[0]
        while parent and parent not in dirs:
            dirs.add(parent)
            parent = parent.rsplit("/", 1)[0]
    lines = [
        f"// Copy overlay files from {src_drv}: onto C:, creating directories.\n",
    ]
    for d in sorted(dirs, key=lambda x: (x.count("/"), x)):
        lines.append(f'DirMk("{d}");\n')
    for i, (dest, _data) in enumerate(items, start=1):
        lines.append(f'Copy("{src_drv}:/F{i:02d}.BIN","{dest}");\n')
        lines.append(f'Del("{dest}.Z");\n')
    lines.append('FileWrite("C:/Tmp/HERMES_OVL_DONE","ok",2);\n')
    lines.append('"OVERLAY DONE\\n";\n')
    return "".join(lines).encode("ascii")


def main() -> int:
    if not STOCK_ISO.is_file() or not DISK.is_file():
        log("missing stock ISO or installed disk")
        return 2
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("")
    # Extend the build overlay with the guest-visible Hermes tree.
    existing = set(build_iso.OVERLAY_PATHS)
    for rel in hermes_overlay():
        if rel not in existing:
            build_iso.OVERLAY_PATHS.append(rel)
            existing.add(rel)

    items = build_iso.overlay_files()
    files: list[tuple[str, bytes]] = [("RUN.HC", make_run_hc_all(items, "D"))]
    for i, (_, data) in enumerate(items, start=1):
        files.append((f"F{i:02d}.BIN", data))
    OVERLAY.write_bytes(make_overlay_fat32.build(files))
    log(f"overlay {OVERLAY} ({OVERLAY.stat().st_size} bytes, {len(items)} files)")

    meta = start_vm(
        "hermes-build2", STOCK_ISO, DISK, memory="2G", boot="d",
        extra=["-drive", f"file={OVERLAY},format=raw,if=ide,index=3,media=disk"],
    )
    log(f"qemu pid {meta['pid']}")
    time.sleep(2)
    qmp = QMP(Path(meta["qmp"]), timeout=60)
    try:
        wait_for(qmp, "Install onto hard drive", timeout=120, prefix="install")
        type_slow(qmp, "n\n")
        wait_for(qmp, "Take Tour", timeout=120, prefix="tour")
        type_slow(qmp, "n\n")
        time.sleep(8)
        log("live shell ready; mounting C: (installed) and D: (overlay)")
        mount_drive(qmp, "C", "1")
        mount_drive(qmp, "D", "3")
        type_slow(qmp, 'Dir("C:/");\n')
        time.sleep(3)
        log("copying overlay from D: to C:")
        type_slow(qmp, 'Cd("D:/");\n#include "D:/RUN.HC";\n')
        over = wait_for(qmp, "OVERLAY DONE", timeout=1800, prefix="overlay")
        (LOG.parent / "overlay-ocr.txt").write_text(over)
        time.sleep(3)
        log("running MakeDistro from C:")
        type_slow(qmp, 'Cd("C:/");\n#include "C:/Adam/Hermes/MakeDistro";\n')
        distro = wait_for(qmp, "ISO written", timeout=5400, prefix="distro")
        (LOG.parent / "distro-ocr.txt").write_text(distro)
        time.sleep(3)
        screen(qmp, "iso-written")
    finally:
        try:
            stop_vm(meta, qmp)
        except Exception:
            pass
        qmp.close()

    raw = RUN / "hermes-build2.raw"
    raw.unlink(missing_ok=True)
    subprocess.check_call(["qemu-img", "convert", "-O", "raw", str(DISK), str(raw)])
    ISO_OUT.parent.mkdir(parents=True, exist_ok=True)
    candidates = [
        "/Tmp/TempleOfHermes.ISO.C",
        "/Tmp/TempleOfHermes.ISO.C.Z",
        "/Tmp/TempleOfHermes.ISO",
    ]
    last_err: Exception | None = None
    for cand in candidates:
        try:
            extract(raw, cand, ISO_OUT)
            log(f"extracted {cand}")
            last_err = None
            break
        except Exception as e:  # try the next RedSea name
            last_err = e
            log(f"extract {cand} failed: {e}")
    if last_err is not None:
        raise last_err
    data = ISO_OUT.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    label = data[16 * 2048 + 40:16 * 2048 + 72].decode("ascii", "replace").strip()
    log(f"ISO label: {label!r}")
    (ISO_OUT.parent / "SHA256SUMS").write_text(f"{digest}  {ISO_OUT.name}\n")
    log(f"ISO {ISO_OUT} ({len(data)} bytes) sha256={digest}")
    raw.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
