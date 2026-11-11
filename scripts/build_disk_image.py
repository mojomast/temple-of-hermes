#!/usr/bin/env python3
"""Build a redistributable, preinstalled Temple of Hermes disk image.

Inputs are an official ISO path and its expected SHA-256.  The installer that
ships on the ISO (Misc/OSInstall.HC -> DoInstall -> the TinkerOS partitioner,
FAT32 formatter, file copy and BootHDIns) is driven inside the guest, exactly
as on a normal install.  The only change to the installed system is that its
stage-2 boot menu is patched to select the installed partition automatically,
so a cold boot with no CD reaches the Hermes launcher without a keypress.

Example (re-run unchanged for a later release):

  python3 scripts/build_disk_image.py \
      --iso TempleOfHermes-0.1.3.ISO \
      --sha256 <hex> \
      --output TempleOfHermes-0.1.3-disk.qcow2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qemu_hermes import QMP, ROOT, glyph_text  # noqa: E402
from hrpc import Hrpc  # noqa: E402
from fat32_read import Fat32  # noqa: E402

DEFAULT_SHA256 = "9afc98ed2bb15a3ff26ebaca12ea392079292df6667b3c1c527fdd30d80cdb13"
DEFAULT_SIZE = 14030848
QEMU = "qemu-system-x86_64"

NOT_LAUNCHER = (
    "Install onto hard drive",
    "Take Tour",
    "System Keys Quick Guide",
    "AutoComplete is in StandBy",
    "TinkerOS Debugger",
)

# The installer prompts and the keys that answer them.  YorN consumes exactly
# one character, so its answers carry no newline; GetI64/GetS consume a line.
INSTALL_PROMPTS = [
    ("Perform automated partitioning and install", b"y"),
    ("How many would you like to install", b"1\n"),
    ("Select graphics mode for drive C:", b"\n"),
    ("also install extra supplemental ISO files", b"n"),
    ("Ready to do install", b"\n"),
]

POST_INSTALL_COMMANDS = [
    'Copy("T:/*.HC","C:/");',
    'Copy("T:/*.DD","C:/");',
    'CopyTree("T:/Home","C:/Home");',
    'CopyTree("T:/Hermes","C:/Hermes");',
    'DirMk("C:/Home");',
    'DirMk("C:/Hermes/Apps/HermesBBS");',
]


def log(msg: str, logfile: Path | None = None) -> None:
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    if logfile:
        logfile.parent.mkdir(parents=True, exist_ok=True)
        with logfile.open("a") as f:
            f.write(line + "\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iso_volume_id(path: Path) -> str:
    """Volume id from the ISO9660 primary volume descriptor (sector 16)."""
    with path.open("rb") as f:
        f.seek(16 * 2048)
        vd = f.read(2048)
    if len(vd) < 88 or vd[0] != 1 or vd[1:6] != b"CD001":
        return ""
    return vd[40:72].decode("latin-1", "replace").strip()


def verify_iso(path: Path, expected: str, expected_size: int | None,
               logfile: Path | None) -> None:
    if not path.is_file():
        raise SystemExit(f"missing ISO: {path}")
    size = path.stat().st_size
    if expected_size and size != expected_size:
        raise SystemExit(f"ISO size {size} != expected {expected_size}")
    got = sha256_file(path)
    if got.lower() != expected.lower():
        raise SystemExit(
            f"ISO sha256 mismatch: got {got}, expected {expected.lower()}")
    log(f"ISO verified: {path} ({size} bytes) sha256={got}", logfile)
    vid = iso_volume_id(path)
    if vid:
        log(f"ISO volume id: {vid}", logfile)


def qemu_start(name: str, rundir: Path, disk: Path | None, iso: Path | None,
               memory: str, width: int = 640, height: int = 480) -> dict:
    rundir.mkdir(parents=True, exist_ok=True)
    for s in rundir.glob("*.sock"):
        s.unlink(missing_ok=True)
    qmp = rundir / "qmp.sock"
    com = rundir / "com1.sock"
    cmd = [
        QEMU, "-name", name,
        "-machine", "pc,kernel-irqchip=off",
        "-accel", "tcg", "-cpu", "qemu64",
        "-m", memory, "-smp", "1", "-vga", "std",
        "-display", "none", "-nic", "none",
        "-qmp", f"unix:{qmp},server=on,wait=off",
        "-serial", f"unix:{com},server=on,wait=off",
        "-boot", "order=c,menu=off",
    ]
    if iso is not None:
        cmd += ["-cdrom", str(iso), "-boot", "order=d,menu=off"]
    if disk is not None:
        cmd += ["-drive", f"file={disk},format=qcow2,if=ide,index=0,media=disk"]
    lf = (rundir / "qemu.log").open("wb")
    proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT)
    meta = {"pid": proc.pid, "cmd": cmd, "qmp": str(qmp), "com1": str(com),
            "rundir": str(rundir)}
    (rundir / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def qemu_stop(meta: dict, q: QMP | None) -> None:
    if q:
        try:
            q.quit()
        except Exception:
            pass
        time.sleep(1)
        try:
            q.close()
        except Exception:
            pass
    pid = int(meta["pid"])
    for sig in (15, 9):
        try:
            os.kill(pid, 0)
        except OSError:
            return
        try:
            os.kill(pid, sig)
        except OSError:
            return
        time.sleep(0.5)


def screendump_text(q: QMP, dest: Path) -> str:
    q.screendump(dest)
    try:
        return glyph_text(dest)
    except Exception:
        return ""


def wait_launcher(q: QMP, rundir: Path, timeout: float,
                  logfile: Path | None, prefix: str = "boot") -> tuple[bool, str]:
    deadline = time.time() + timeout
    last = ""
    n = 0
    while time.time() < deadline:
        n += 1
        last = screendump_text(q, rundir / f"{prefix}-{n:03d}.png")
        low = last.lower()
        if ("hermes apps" in low or "click an icon" in low) and \
                not any(p.lower() in low for p in NOT_LAUNCHER):
            return True, last
        time.sleep(2)
    return False, last


def close_launcher(q: QMP, rundir: Path, logfile: Path | None) -> None:
    """Close the live-ISO launcher so the installer terminal owns the screen."""
    for _ in range(5):
        t = screendump_text(q, rundir / "close.png")
        if "hermes apps" not in t.lower() and "click an icon" not in t.lower():
            return
        q.send_qcodes("shift", "esc")
        time.sleep(1.2)


def hrpc_connect(path: Path, timeout: float = 60.0) -> Hrpc:
    deadline = time.time() + timeout
    last: Exception | None = None
    while time.time() < deadline:
        try:
            h = Hrpc(path, timeout=20)
            h.request("ping", b"", timeout=15)
            return h
        except Exception as e:  # noqa: BLE001
            last = e
            try:
                h.close()
            except Exception:
                pass
            time.sleep(2)
    raise RuntimeError(f"HRPC not ready: {last}")


def prepare_installer(meta: dict, q: QMP, rundir: Path,
                      logfile: Path | None) -> tuple[QMP, tuple[int, int, int, int]]:
    """Spawn a visible terminal that runs the ISO's own DoInstall."""
    h = hrpc_connect(Path(meta["com1"]))
    src = ('User("Cd(\\"T:/\\");'
           '\\n#define __CMD_LINE__ 0'
           '\\n#include \\"T:/Misc/OSInstall.HC\\";'
           '\\nDoInstall(TRUE);\\n");')
    h.request("eval", src.encode(), timeout=30)
    time.sleep(3)
    st, d = h.request("windows", b"", timeout=20)
    windows = json.loads(d.decode()).get("windows", [])
    cand = [w for w in windows if w.get("title") != "Hermes Apps"]
    if not cand:
        raise RuntimeError("installer terminal did not appear")
    win = cand[0]
    addr = win["addr"]
    h.request("focus", str(addr).encode(), timeout=20)
    time.sleep(1)
    b = win["win"]
    q.mouse_click_at((b[0] + b[2]) // 2 * 8, (b[1] + b[3]) // 2 * 8)
    time.sleep(1)
    # The Hermes daemon writes COM1 events; the 0.1.2 daemon faults if the
    # installer's IRQ/probe work interrupts a serial write.  Stop it for the
    # install, exactly as the stock installer runs without a daemon.
    try:
        h.request("eval", b"Kill(hermes_task,FALSE);", timeout=5)
    except Exception:
        pass
    try:
        h.close()
    except Exception:
        pass
    log(f"installer terminal {addr}; daemon stopped", logfile)
    return q, tuple(b)


def drive_install(q: QMP, rundir: Path, bounds: tuple[int, int, int, int],
                  logfile: Path | None, timeout: float) -> bool:
    """Answer the installer prompts; returns True once 'Reboot Now' is answered."""
    ai = 0
    deadline = time.time() + timeout
    while time.time() < deadline and ai < len(INSTALL_PROMPTS):
        time.sleep(1.2)
        t = screendump_text(q, rundir / "prompt.png")
        low = t.lower()
        if ai < len(INSTALL_PROMPTS) and INSTALL_PROMPTS[ai][0].lower() in low:
            log(f"prompt: {INSTALL_PROMPTS[ai][0]!r}", logfile)
            q.type_text(INSTALL_PROMPTS[ai][1].decode(), delay=0.15)
            ai += 1
            time.sleep(1.0)
        else:
            bad = [p for p in ("TinkerOS Debugger", "Unhandled Exception")
                   if p.lower() in low]
            if bad:
                log(f"guest failure text: {bad}", logfile)
                return False
    if ai < len(INSTALL_PROMPTS):
        log(f"installer prompts not reached ({ai}/{len(INSTALL_PROMPTS)})", logfile)
        return False
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(2)
        t = screendump_text(q, rundir / "install.png")
        low = t.lower()
        if "reboot now" in low:
            q.type_text("n", delay=0.2)
            log("install finished; Reboot Now answered n", logfile)
            return True
        if "tinkeros debugger" in low or "unhandled exception" in low:
            log("guest entered the debugger during install", logfile)
            return False
    log("timed out waiting for Reboot Now", logfile)
    return False


def post_install_copy(q: QMP, rundir: Path, bounds: tuple[int, int, int, int],
                      logfile: Path | None) -> None:
    """Copy the Hermes tree and home files, then create the writable dirs."""
    time.sleep(4)
    b = bounds
    q.mouse_click_at((b[0] + b[2]) // 2 * 8, (b[1] + b[3]) // 2 * 8)
    time.sleep(1)
    q.type_text("\n", delay=0.1)
    time.sleep(1)
    for cmd in POST_INSTALL_COMMANDS:
        log(f"post-install: {cmd}", logfile)
        q.type_text(cmd + "\n", delay=0.04)
        time.sleep(12 if "Hermes" in cmd else 3)
    time.sleep(3)
    t = screendump_text(q, rundir / "post-install.png")
    log(f"post-install screen tail: {t[-300:]!r}", logfile)


def mbr_partition(raw: Path) -> tuple[int, int]:
    data = raw.read_bytes()[:512]
    if data[510:512] != b"\x55\xaa":
        raise SystemExit("installed image has no MBR signature")
    for i in range(4):
        e = data[0x1BE + i * 16:0x1BE + (i + 1) * 16]
        if e[4] in (0x0B, 0x0C, 0x0E) and int.from_bytes(e[8:12], "little"):
            return int.from_bytes(e[8:12], "little"), i
    raise SystemExit("no FAT32 partition in installed MBR")


def check_installed(raw: Path, logfile: Path | None) -> None:
    lba, _ = mbr_partition(raw)
    fs = Fat32(raw, lba)
    try:
        needed_files = [
            "Kernel.BIN.C",
            "StartOS.HC",
            "Once.HC",
            "Home/Once.HC",
            "Home/HomeSys.HC",
            "Hermes/Apps/Launcher/Run.HC",
            "Hermes/Apps/Registry.HC",
        ]
        for rel in needed_files:
            if fs.resolve(rel) is None:
                raise SystemExit(f"installed C: is missing {rel}")
        if fs.resolve("Hermes/Apps/HermesBBS") is None:
            raise SystemExit("installed C: is missing Hermes/Apps/HermesBBS")
        log(f"installed filesystem verified (partition LBA {lba})", logfile)
    finally:
        fs.close()


def patch_boot_menu(raw: Path, logfile: Path | None) -> None:
    """Make the TinkerOS stage-2 menu select the installed partition.

    The TinkerOS master boot loader always prints a menu and waits for a
    digit.  BootMHDIns lists 'Old MBR' first (it saved one) and the installed
    FAT32 partition second, so replacing the single-key read with AL='1'
    selects the installed partition without a keypress.  The MBR, partition
    table, FAT32 filesystem, partition boot record and kernel are untouched.
    """
    lba, _ = mbr_partition(raw)
    fs = Fat32(raw, lba)
    try:
        if fs.resolve("0000Boot/OldMBR.BIN.C") is None:
            raise SystemExit("stage-2 menu has no OldMBR entry; refusing to patch")
        c, size, attr = fs.resolve("0000Boot/BootMHD2.BIN.C")
        data = fs.read_file("0000Boot/BootMHD2.BIN.C")
        off = fs.base + fs.data_off + (c - 2) * fs.spc * fs.bps
    finally:
        fs.close()
    i = data.find(b"\xbe\x3c\x00\xe8")
    if i < 0:
        raise SystemExit("stage-2 menu signature not found")
    call_off = i + 6
    if data[call_off:call_off + 3] == b"\xb0\x31\x90":
        log("boot menu already auto-selects the installed partition", logfile)
        return
    if data[call_off:call_off + 5] != b"\xe8\xd1\xff\x3c\x30":
        raise SystemExit("unexpected stage-2 menu byte pattern")
    buf = bytearray(raw.read_bytes())
    buf[off + call_off:off + call_off + 3] = b"\xb0\x31\x90"
    raw.write_bytes(buf)
    log("patched stage-2 boot menu to auto-select Drive C", logfile)


def convert_compressed(raw: Path, output: Path, logfile: Path | None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    tmp.unlink(missing_ok=True)
    subprocess.check_call([
        "qemu-img", "convert", "-f", "raw", "-O", "qcow2",
        "-c", "-o", "cluster_size=65536", str(raw), str(tmp),
    ])
    subprocess.check_call(["qemu-img", "check", str(tmp)])
    os.replace(tmp, output)


def write_sums(output: Path, iso: Path, logfile: Path | None,
               sums: Path | None = None) -> Path:
    if sums is None:
        sums = output.with_name(output.stem + ".SHA256SUMS")
    rows = []
    for p in (output, iso):
        if p.is_file():
            rows.append(f"{sha256_file(p)}  {p.name}")
    sums.write_text("\n".join(rows) + "\n")
    log(f"wrote {sums}", logfile)
    return sums


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--iso", required=True, type=Path)
    ap.add_argument("--sha256", required=True,
                    help="expected ISO SHA-256 (required)")
    ap.add_argument("--iso-size", type=int, default=None,
                    help="optional expected ISO size in bytes")
    ap.add_argument("--output", type=Path,
                    default=ROOT / "dist" / "TempleOfHermes-0.1.2-disk.qcow2")
    ap.add_argument("--work-dir", type=Path, default=ROOT / "run" / "disk-image")
    ap.add_argument("--size", default="4G")
    ap.add_argument("--memory", default="2G")
    ap.add_argument("--timeout", type=float, default=1800.0,
                    help="bounded install wait in seconds")
    ap.add_argument("--sums", type=Path, default=None,
                    help="checksum file to write (default <output-stem>.SHA256SUMS)")
    ap.add_argument("--keep-work", action="store_true")
    args = ap.parse_args()

    work = args.work_dir
    work.mkdir(parents=True, exist_ok=True)
    logfile = work / "build.log"
    log(f"build start: {args.iso} -> {args.output}", logfile)
    verify_iso(args.iso, args.sha256, args.iso_size, logfile)

    disk = work / "install.qcow2"
    if disk.exists():
        disk.unlink()
    subprocess.check_call(["qemu-img", "create", "-f", "qcow2",
                           str(disk), args.size])
    log(f"created blank disk {disk} ({args.size})", logfile)

    meta = qemu_start("hermes-disk-install", work / "vm-install", disk,
                      args.iso, args.memory)
    q = QMP(Path(meta["qmp"]), timeout=60)
    ok = False
    try:
        time.sleep(1)
        up, text = wait_launcher(q, work / "vm-install", 120, logfile)
        log(f"live ISO launcher: {up}", logfile)
        if not up:
            raise RuntimeError("live ISO did not reach the launcher")
        close_launcher(q, work / "vm-install", logfile)
        q, bounds = prepare_installer(meta, q, work / "vm-install", logfile)
        ok = drive_install(q, work / "vm-install", bounds, logfile, args.timeout)
        if not ok:
            raise RuntimeError("installer did not complete")
        post_install_copy(q, work / "vm-install", bounds, logfile)
    finally:
        qemu_stop(meta, q)

    raw = work / "installed.raw"
    subprocess.check_call(["qemu-img", "convert", "-f", "qcow2", "-O", "raw",
                           str(disk), str(raw)])
    check_installed(raw, logfile)
    patch_boot_menu(raw, logfile)
    convert_compressed(raw, args.output, logfile)

    info = subprocess.check_output(["qemu-img", "info", "--output=json",
                                    str(args.output)])
    info = json.loads(info)
    digest = sha256_file(args.output)
    log(f"output {args.output}", logfile)
    log(f"virtual-size={info.get('virtual-size')} "
        f"actual-size={args.output.stat().st_size} sha256={digest}", logfile)
    sums = write_sums(args.output, args.iso, logfile, args.sums)
    summary = {
        "iso": str(args.iso),
        "iso_sha256": sha256_file(args.iso),
        "iso_bytes": args.iso.stat().st_size,
        "image": str(args.output),
        "image_sha256": digest,
        "image_bytes": args.output.stat().st_size,
        "virtual_size": info.get("virtual-size"),
        "format": info.get("format"),
        "compressed": True,
        "sha256sums": str(sums),
    }
    (work / "build-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if not args.keep_work:
        for p in (raw,):
            p.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
