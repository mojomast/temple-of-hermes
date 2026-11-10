#!/usr/bin/env python3
"""Install TinkerOS 5.20-rc10 to a qcow2, overlay THE TEMPLE OF HERMES sources,
run TinkerOS's own DoDistro/BootDVDIns/RedSeaISO path, and extract the ISO.

This is slow under TCG (no usable /dev/kvm on this builder).
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qemu_hermes import (  # noqa: E402
    QMP,
    RUN,
    ROOT,
    STOCK_ISO,
    SHOTS,
    Serial,
    glyph_text,
    start_vm,
    stop_vm,
    wait_for_text,
)

NAME = "hermes-build"
DISK = RUN / "hermes-build.qcow2"
SHOT = SHOTS / "_raw" / "build"
LOG = RUN / "build.log"
SERIAL_LOG = RUN / "build-com1.bin"
DIST = ROOT / "dist"
ISO_NAME = "TempleOfHermes-0.1.1.ISO"

OVERLAY_PATHS = [
    "Adam/Hermes/Glbls.HC",
    "Adam/Hermes/Protocol.HC",
    "Adam/Hermes/StateDir.HC",
    "Adam/Hermes/Text.HC",
    "Adam/Hermes/Events.HC",
    "Adam/Hermes/Presence.HC",
    "Adam/Hermes/Guards.HC",
    "Adam/Hermes/Files.HC",
    "Adam/Hermes/Daemon.HC",
    "Adam/Hermes/Load.HC",
    "Adam/Hermes/MakeDistro.HC",
    "Adam/Hermes/VERSION",
    "Once.HC",
    "HomeSys.HC",
    "MakeHome.HC",
    "Home/MakeHome.HC",
    "Home/DoDistro.HC",
    "Doc/Start.DD",
    "Kernel/StrC.HC",
    "Kernel/KGlbls.HC",
    "Kernel/KernelC.HH",
    "Kernel/BlkDev/DskFmt.HC",
    "Misc/OSInstall.HC",
    "Adam/Opt/Boot/BootHDIns.HC",
]


def log(msg: str) -> None:
    line = time.strftime("%H:%M:%S") + " " + msg
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def dest_paths(rel: str) -> list[str]:
    """Where the file should land on C:."""
    rel = rel.replace("\\", "/")
    outs = [f"C:/{rel}"]
    # Home/Once is what `#include "Once"` finds; also drop a copy at /Home.
    if rel == "Once.HC":
        outs.append("C:/Home/Once.HC")
    if rel == "HomeSys.HC":
        outs.append("C:/Home/HomeSys.HC")
    if rel == "MakeHome.HC":
        outs.append("C:/Home/MakeHome.HC")
    return outs


def z_siblings(path: str) -> list[str]:
    # TempleOS compressed twins we must not leave behind.
    return [path + ".Z"]


def overlay_files() -> list[tuple[str, bytes]]:
    items: list[tuple[str, bytes]] = []
    dels: list[str] = []
    for rel in OVERLAY_PATHS:
        src = ROOT / rel
        if not src.is_file():
            raise FileNotFoundError(src)
        data = src.read_bytes()
        # Strip a UTF-8 BOM if any; HolyC wants ASCII/Latin-1.
        if data.startswith(b"\xef\xbb\xbf"):
            data = data[3:]
        for dest in dest_paths(rel):
            items.append((dest, data))
            dels.extend(z_siblings(dest))
    script_lines = ["// AfterOverlay - remove compressed twins of patched files.\n"]
    for z in dels:
        script_lines.append(f'Del("{z}");\n')
    items.append(("C:/Tmp/AfterOverlay.HC", "".join(script_lines).encode("ascii")))
    return items


def shot(qmp: QMP, name: str) -> Path:
    dest = SHOT / f"{name}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    qmp.screendump(dest)
    try:
        text = glyph_text(dest)
        (SHOT / f"{name}.txt").write_text(text)
        log(f"shot {name}: {text[:160]!r}")
    except Exception as e:
        log(f"shot {name}: ocr failed {e}")
    return dest


def install_to_disk() -> None:
    """Install stock TinkerOS onto DISK and stop at the post-install prompt.

    This is the install-wizard half only.  The Hermes sources are delivered by
    the separate FAT32 overlay, never by typing CommInit at this shell.
    """
    if not STOCK_ISO.is_file():
        raise FileNotFoundError(f"missing stock ISO: {STOCK_ISO}")
    RUN.mkdir(parents=True, exist_ok=True)
    SHOT.mkdir(parents=True, exist_ok=True)
    if DISK.exists():
        DISK.unlink()
    subprocess.check_call(["qemu-img", "create", "-f", "qcow2", str(DISK), "4G"])
    log(f"disk {DISK}")
    meta = start_vm(NAME, STOCK_ISO, DISK, memory="2G", boot="d")
    log(f"qemu pid {meta['pid']}")
    time.sleep(1)
    qmp = QMP(Path(meta["qmp"]), timeout=60)
    ser = Serial(Path(meta["com1"]), timeout=60, log=SERIAL_LOG)
    try:
        log("waiting for first-boot install prompt")
        wait_for_text(qmp, SHOT, "Install onto hard drive", timeout=900, interval=10, prefix="boot")
        shot(qmp, "01-install-prompt")
        qmp.type_text("y\n", delay=0.14)
        wait_for_text(qmp, SHOT, "automated partitioning", timeout=300, interval=6, prefix="wiz1")
        shot(qmp, "02-automated")
        qmp.type_text("y\n", delay=0.14)
        wait_for_text(qmp, SHOT, "would you like to install", timeout=180, interval=5, prefix="howmany")
        shot(qmp, "03-how-many")
        qmp.type_text("1\n", delay=0.14)
        wait_for_text(qmp, SHOT, "Select graphics mode for drive C:", timeout=180, interval=5, prefix="gfx")
        shot(qmp, "04-graphics")
        qmp.type_text("\n", delay=0.14)  # default 640x480
        wait_for_text(qmp, SHOT, "would you like to also install extra", timeout=180, interval=5, prefix="extras")
        shot(qmp, "05-extras")
        qmp.type_text("n\n", delay=0.14)
        log("waiting for install copy / Reboot Now")
        wait_for_text(qmp, SHOT, "Reboot Now (y or n", timeout=1800, interval=10, prefix="install")
        shot(qmp, "07-reboot-now")
        qmp.type_text("n\n", delay=0.14)
        time.sleep(3)
        shot(qmp, "08-installed")
    finally:
        log("stopping VM after install")
        ser.close()
        stop_vm(meta, qmp)
        qmp.close()
    log(f"installed disk kept at {DISK}")


def main() -> int:
    install_to_disk()
    sys.path.insert(0, str(ROOT / "shots" / "hermes-integration"))
    from build_from_installed import main as build_from_installed_main

    return build_from_installed_main()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"BUILD FAILED: {type(e).__name__}: {e}")
        raise
