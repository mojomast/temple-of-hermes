#!/usr/bin/env python3
"""Install TinkerOS 5.20-rc10 to a qcow2, overlay THE TEMPLE OF HERMES sources,
run TinkerOS's own DoDistro/BootDVDIns/RedSeaISO path, and extract the ISO.

This is slow under TCG (no usable /dev/kvm on this builder).
"""
from __future__ import annotations

import hashlib
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fat32_read import extract, open_first_fat  # noqa: E402
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
ISO_NAME = "TempleOfHermes-0.1.0.ISO"

# Compact serial file receiver, typed at the HolyC prompt after install.
RECEIVER = (
    "CommInit;CommInit8n1(1,115200);\n"
    "U0 R(){U8 n[256],*p,c;I64 i,len,k;DirMk(\"C:/Adam/Hermes\");"
    "while(1){i=0;while((c=CommGetChar(1))&&i<255)n[i++]=c;n[i]=0;"
    "if(!StrCmp(n,\"END\"))break;len=0;for(k=0;k<4;k++)"
    "len|=CommGetChar(1)<<(8*k);p=MAlloc(len+1);"
    "for(k=0;k<len;k++)p[k]=CommGetChar(1);p[len]=0;"
    "FileWrite(n,p,len);Free(p);CommPutS(1,\"OK\\n\");}}\n"
    "R;\n"
)

OVERLAY_PATHS = [
    "Adam/Hermes/Glbls.HC",
    "Adam/Hermes/Protocol.HC",
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
    script_lines = ["// AfterOverlay — remove compressed twins of patched files.\n"]
    for z in dels:
        script_lines.append(f'Del("{z}");\n')
    items.append(("C:/Tmp/AfterOverlay.HC", "".join(script_lines).encode("ascii")))
    return items


def send_overlay(ser: Serial, files: list[tuple[str, bytes]]) -> None:
    for dest, data in files:
        log(f"push {dest} ({len(data)} bytes)")
        frame = dest.encode("ascii") + b"\x00" + struct.pack("<I", len(data)) + data
        ser.write(frame)
        # OK\n from the guest
        got = ser.read_until(b"OK\n", timeout=30.0)
        log(f"  ack {got!r}")
    ser.write(b"END\x00")
    log("overlay complete")


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


def main() -> int:
    if not STOCK_ISO.is_file():
        log(f"missing stock ISO: {STOCK_ISO}")
        return 2
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
        qmp.type_text("y\n")
        wait_for_text(qmp, SHOT, "automated partitioning", timeout=300, interval=6, prefix="wiz1")
        shot(qmp, "02-automated")
        qmp.type_text("y\n")
        wait_for_text(qmp, SHOT, "How many", timeout=180, interval=5, prefix="howmany")
        shot(qmp, "03-how-many")
        qmp.type_text("1\n")
        wait_for_text(qmp, SHOT, "graphics mode", timeout=180, interval=5, prefix="gfx")
        shot(qmp, "04-graphics")
        qmp.type_text("\n")  # default 640x480
        wait_for_text(qmp, SHOT, "extra", timeout=180, interval=5, prefix="extras")
        shot(qmp, "05-extras")
        qmp.type_text("n\n")
        wait_for_text(qmp, SHOT, "Press a key", timeout=180, interval=5, prefix="press")
        shot(qmp, "06-press-key")
        qmp.type_text("\n")
        log("waiting for install copy / Reboot Now")
        wait_for_text(qmp, SHOT, "Reboot Now", timeout=2400, interval=15, prefix="install")
        shot(qmp, "07-reboot-now")
        qmp.type_text("n\n")
        time.sleep(2)
        # Leave the Install.DD editor if it still has focus.
        qmp.send_qcodes("shift", "esc")
        time.sleep(0.4)
        qmp.send_qcodes("shift", "esc")
        time.sleep(0.6)
        qmp.type_text("\n")
        shot(qmp, "08-after-install")
        log("typing serial receiver")
        qmp.type_text(RECEIVER, delay=0.07)
        time.sleep(2)
        shot(qmp, "09-receiver")
        files = overlay_files()
        send_overlay(ser, files)
        time.sleep(1)
        qmp.send_qcodes("shift", "esc")
        time.sleep(0.3)
        qmp.type_text("\n#include \"C:/Tmp/AfterOverlay.HC\";\n", delay=0.07)
        time.sleep(2)
        shot(qmp, "10-after-overlay")
        log("starting in-guest DoDistro / BootDVDIns (very slow under TCG)")
        qmp.type_text('C:;\nCd("/");\n#include "C:/Adam/Hermes/MakeDistro";\n', delay=0.07)
        wait_for_text(
            qmp,
            SHOT,
            "ISO written",
            timeout=5400,
            interval=20,
            prefix="distro",
        )
        shot(qmp, "11-iso-written")
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
    # List /Tmp so we can see the ISO name
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
    candidates = [
        "/Tmp/TempleOfHermes.ISO.C",
        "/Tmp/TempleOfHermes.ISO.C.Z",
        "/Tmp/TEMPLEOF.ISO",
        "/Tmp/TempleOfHermes.ISO",
    ]
    last_err = None
    for cand in candidates:
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
    # Keep a copy of the raw only if something went wrong; it's large, drop it on success.
    raw.unlink(missing_ok=True)
    log("build finished")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"BUILD FAILED: {type(e).__name__}: {e}")
        raise
