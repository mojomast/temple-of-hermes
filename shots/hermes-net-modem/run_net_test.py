#!/usr/bin/env python3
"""Bounded QEMU TCG test for the Modem / Net app and the COM2 echo path.

It builds a temporary MBR+FAT32 overlay with the real Hermes/Net and
Hermes/Apps/Net sources, boots the public TinkerOS 5.20-rc10 live CD with no
NIC, attaches a local loopback-only AT stub to COM2's unix socket, runs
Run.HC twice, and runs HermesNetEchoTest without contacting a BBS or a VPS.

Only Python/PIL is used to inspect the captured PNGs; no image is displayed.
"""
from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "shots" / "hermes-net-modem"
RAW = OUT / "raw"
DISK = RAW / "net-overlay.img"
ISO = Path(os.environ.get("TOH_ISO", "/tmp/toh-iso/TinkerOS_5.20-rc10.ISO"))
ISO_SHA256 = "feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4"
QEMU = "qemu-system-x86_64"
EGA = [
    (0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170),
    (170, 0, 0), (170, 0, 170), (170, 85, 0), (170, 170, 170),
    (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255),
    (255, 85, 85), (255, 85, 255), (255, 255, 85), (255, 255, 255),
]
EGA_SET = set(EGA)


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S") + " " + msg, flush=True)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qcodes_for(ch: str) -> list[str]:
    shift = {
        "A": "a", "B": "b", "C": "c", "D": "d", "E": "e", "F": "f", "G": "g",
        "H": "h", "I": "i", "J": "j", "K": "k", "L": "l", "M": "m", "N": "n",
        "O": "o", "P": "p", "Q": "q", "R": "r", "S": "s", "T": "t", "U": "u",
        "V": "v", "W": "w", "X": "x", "Y": "y", "Z": "z",
        '"': "apostrophe", ":": "semicolon", "_": "minus", "+": "equal",
        "{": "bracket_left", "}": "bracket_right", "|": "backslash",
        "<": "comma", ">": "dot", "?": "slash",
        "!": "1", "@": "2", "#": "3", "$": "4", "%": "5",
        "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
        "~": "grave_accent",
    }
    plain = {
        " ": "spc", "\n": "ret", "\t": "tab", "-": "minus", "=": "equal",
        "[": "bracket_left", "]": "bracket_right", "\\": "backslash",
        ";": "semicolon", "'": "apostrophe", ",": "comma", ".": "dot",
        "/": "slash", "`": "grave_accent",
    }
    if ch in shift:
        return ["shift", shift[ch]]
    if ch in plain:
        return [plain[ch]]
    if "a" <= ch <= "z" or "0" <= ch <= "9":
        return [ch]
    raise ValueError(f"no qcode for {ch!r}")


class QMP:
    def __init__(self, path: Path, timeout: float = 60.0):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.buf = b""
        deadline = time.time() + timeout
        last: Exception | None = None
        while time.time() < deadline:
            try:
                self.sock.connect(str(path))
                break
            except OSError as exc:
                last = exc
                time.sleep(0.1)
        else:
            raise RuntimeError(f"QMP connect failed: {last}")
        self._read_obj()
        self.cmd("qmp_capabilities")

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def _read_obj(self) -> dict:
        while True:
            if b"\n" in self.buf:
                line, self.buf = self.buf.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line.decode())
                if "event" in obj:
                    continue
                return obj
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError("QMP socket closed")
            self.buf += chunk

    def cmd(self, execute: str, **arguments) -> dict:
        msg = {"execute": execute}
        if arguments:
            msg["arguments"] = arguments
        self.sock.sendall((json.dumps(msg) + "\n").encode())
        resp = self._read_obj()
        if "error" in resp:
            raise RuntimeError(f"QMP {execute}: {resp['error']}")
        return resp

    def send_key(self, *codes: str, hold: int = 80) -> None:
        keys = [{"type": "qcode", "data": c} for c in codes]
        self.cmd("send-key", keys=keys, **{"hold-time": hold})

    def type_text(self, text: str, delay: float = 0.09) -> None:
        for ch in text:
            self.send_key(*qcodes_for(ch))
            time.sleep(delay)

    def screendump(self, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.cmd("screendump", filename=str(dest), format="png")

    def quit(self) -> None:
        try:
            self.cmd("quit")
        except Exception:
            pass


class ComReader(threading.Thread):
    """Drain COM1 and keep text markers; never blocks the guest."""

    def __init__(self, path: Path):
        super().__init__(daemon=True)
        self.path = path
        self.stop_event = threading.Event()
        self.data = bytearray()
        self.error: str | None = None

    def run(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        deadline = time.time() + 30.0
        while time.time() < deadline:
            try:
                sock.connect(str(self.path))
                break
            except OSError as exc:
                self.error = f"{type(exc).__name__}: {exc}"
                time.sleep(0.1)
        else:
            return
        try:
            while not self.stop_event.is_set():
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                self.data.extend(chunk)
        except OSError as exc:
            self.error = f"{type(exc).__name__}: {exc}"
        finally:
            try:
                sock.close()
            except OSError:
                pass

    def wait_for(self, needle: bytes, timeout: float) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if needle in self.data:
                return True
            time.sleep(0.2)
        return needle in self.data

    def stop(self) -> None:
        self.stop_event.set()
        self.join(timeout=2.0)

    def text(self) -> str:
        return bytes(self.data).decode("ascii", "replace")


def pil_check(png: Path) -> dict:
    im = Image.open(png)
    size = list(im.size)
    rgb = im.convert("RGB")
    pixels = list(rgb.getdata())
    off = [c for c in pixels if c not in EGA_SET]
    mapped = sorted({min(range(16), key=lambda i: sum((c[j] - EGA[i][j]) ** 2 for j in range(3))) for c in set(pixels)})
    bbox = list(rgb.convert("L").getbbox() or (0, 0, 0, 0))
    return {
        "path": str(png.relative_to(ROOT)),
        "size": size,
        "mode": im.mode,
        "mapped_palette_indices": mapped,
        "palette_0_15": max(mapped) <= 15 if mapped else False,
        "off_palette_pixels": len(off),
        "unique_colors": len(set(pixels)),
        "bbox": bbox,
    }


def make_driver(files: list[tuple[str, str]]) -> str:
    lines = [
        "// Auto-generated Modem/Net test driver.\n",
        'DirMk("B:/Hermes");\n',
        'DirMk("B:/Hermes/Net");\n',
        'DirMk("B:/Hermes/Apps");\n',
        'DirMk("B:/Hermes/Apps/Net");\n',
        'DirMk("B:/Hermes/Art");\n',
        'DirMk("B:/Hermes/Art/Icons");\n',
        'DirMk("B:/Hermes/Art/Icons/32");\n',
        'DirMk("C:/Tmp");\n',
        'CommInit;\n',
        'CommInit8n1(1,115200);\n',
        'CommPutS(1,"NET_START\\n");\n',
    ]
    for idx, (src, dest) in enumerate(files, start=1):
        lines.append(f'Copy("C:/F{idx:02d}.BIN","{dest}");\n')
        lines.append(f'Del("{dest}.Z");\n')
    lines.append('FileWrite("C:/Tmp/NET_STAGED","ok",2);\n')
    lines.append('CommPutS(1,"NET_STAGED\\n");\n')
    lines.append('"\\n== Modem / Net Run.HC (1) ==\\n";\n')
    lines.append('#include "B:/Hermes/Apps/Net/Run.HC";\n')
    lines.append('FileWrite("C:/Tmp/NET_RUN1","ok",2);\n')
    lines.append('CommPutS(1,"NET_RUN1\\n");\n')
    lines.append('Sleep(2000);\n')
    lines.append('"\\n== Modem / Net Run.HC (2) ==\\n";\n')
    lines.append('#include "B:/Hermes/Apps/Net/Run.HC";\n')
    lines.append('FileWrite("C:/Tmp/NET_RUN2","ok",2);\n')
    lines.append('CommPutS(1,"NET_RUN2\\n");\n')
    lines.append('FileWrite("C:/Tmp/NET_READY","ok",2);\n')
    return "".join(lines)


ECHO_DRIVER = r'''
U0 NetEchoDriver()
{
  I64 r;
  U8 *rr;
  U8 *p;
  CommPutS(1,"NET_ECHO_START\n");
  r=HermesNetEchoTest;
  rr=MStrPrint("%d",r);
  FileWrite("C:/Tmp/NET_ECHO.RES",rr,StrLen(rr));
  Free(rr);
  p=MStrPrint("result=%d tx_len=%d rx_len=%d tx=%s rx=%s\n",
    r,hermes_net_echo_tx_len,hermes_net_echo_rx_len,
    hermes_net_echo_tx,hermes_net_echo_rx);
  FileWrite("C:/Tmp/NET_ECHO_GUEST",p,StrLen(p));
  Free(p);
  FileWrite("C:/Tmp/NET_ECHO_DONE","ok",2);
  CommPutS(1,"NET_ECHO_END\n");
}
NetEchoDriver;
'''


def build_overlay(files: list[tuple[str, str]]) -> None:
    builder = load_module("art_build_overlay", ROOT / "shots" / "hermes-art" / "tools" / "build_overlay.py")
    run_hc = make_driver(files).encode("ascii")
    echo_hc = (ECHO_DRIVER.strip() + "\n").encode("ascii")
    entries: list[tuple[str, bytes]] = [("RUN.HC", run_hc), ("ECHO.HC", echo_hc)]
    for idx, (_src, dest) in enumerate(files, start=1):
        data = (ROOT / _src).read_bytes()
        entities = (f"F{idx:02d}.BIN", data)
        entries.append(entities)
        log(f"overlay {entities[0]} -> {dest} ({len(data)} bytes)")
    RAW.mkdir(parents=True, exist_ok=True)
    DISK.write_bytes(builder.build(entries))
    log(f"overlay image {DISK.name} ({DISK.stat().st_size} bytes)")


def read_guest_file(path: str) -> str | None:
    fat = load_module("fat32_read", ROOT / "scripts" / "fat32_read.py")
    try:
        fs = fat.open_first_fat(DISK)
        try:
            return fs.read_file(path).decode("latin1", "replace")
        finally:
            fs.close()
    except Exception:
        return None


def main() -> int:
    if not ISO.is_file():
        log(f"missing ISO {ISO.name}")
        return 2
    RAW.mkdir(parents=True, exist_ok=True)
    for old in RAW.glob("*.sock"):
        old.unlink(missing_ok=True)

    files = [
        ("Hermes/Net/Glbls.HC", "B:/Hermes/Net/Glbls.HC"),
        ("Hermes/Net/Protocol.HC", "B:/Hermes/Net/Protocol.HC"),
        ("Hermes/Net/Modem.HC", "B:/Hermes/Net/Modem.HC"),
        ("Hermes/Net/Load.HC", "B:/Hermes/Net/Load.HC"),
        ("Hermes/Net/Build.HC", "B:/Hermes/Net/Build.HC"),
        ("Hermes/Apps/Net/Net.HC", "B:/Hermes/Apps/Net/Net.HC"),
        ("Hermes/Apps/Net/Load.HC", "B:/Hermes/Apps/Net/Load.HC"),
        ("Hermes/Apps/Net/Run.HC", "B:/Hermes/Apps/Net/Run.HC"),
        ("Hermes/Art/Icons/32/modem-net.GR", "B:/Hermes/Art/Icons/32/modem-net.GR"),
    ]
    build_overlay(files)

    qmp_sock = RAW / "qmp.sock"
    com1_sock = RAW / "com1.sock"
    com2_sock = RAW / "com2.sock"
    qemu_log = RAW / "qemu.log"
    stub_log = OUT / "com-echo.log"
    stub = None
    proc = None
    qmp = None
    com1 = None
    status: dict = {"iso": ISO.name, "iso_sha256": ISO_SHA256, "com": "COM2",
                    "socket": com2_sock.name, "shots": {}, "guest": {}, "errors": []}

    qemu_cmd = [
        QEMU,
        "-name", "hermes-net-modem",
        "-machine", "pc,kernel-irqchip=off",
        "-accel", "tcg", "-cpu", "qemu64",
        "-m", "2G", "-smp", "1",
        "-vga", "std", "-display", "none", "-nic", "none",
        "-qmp", f"unix:{qmp_sock},server=on,wait=off",
        "-serial", f"unix:{com1_sock},server=on,wait=off",
        "-serial", f"unix:{com2_sock},server=on,wait=off",
        "-cdrom", str(ISO),
        "-boot", "order=d,menu=off",
        "-drive", f"file={DISK},format=raw,if=ide,index=1,media=disk",
    ]
    try:
        stub_log.write_text(
            "Local COM2 echo stub for Modem / Net acceptance.\n"
            "COM2 is the second QEMU serial port; COM1 is left to Hermes HRPC.\n"
            "COM1-socket echo was not used: COM1 is the HRPC console, so the\n"
            "existing Hermes/Net modem path on COM2 carries the echo test.\n"
            f"QEMU COM2 socket: {com2_sock.name}\n"
            f"ISO: {ISO.name} sha256={ISO_SHA256}\n"
            "Transport: in-memory loopback.  No BBS, VPS, DNS, or deploy.\n\n",
            encoding="utf-8",
        )
        lf = qemu_log.open("wb")
        proc = subprocess.Popen(qemu_cmd, stdout=lf, stderr=lf)
        status["qemu_pid"] = proc.pid
        time.sleep(1)
        qmp = QMP(qmp_sock, timeout=120)
        com1 = ComReader(com1_sock)
        com1.start()
        stub = subprocess.Popen(
            [sys.executable, str(OUT / "com2_echo_stub.py"), str(com2_sock),
             str(stub_log), "--timeout", "600", "--allow", "hermes"],
            cwd=str(ROOT),
        )
        status["stub_pid"] = stub.pid
        log("boot live CD (TCG)")
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
        qmp.screendump(OUT / "02-overlay-listed.png")
        status["shots"]["02-overlay-listed"] = pil_check(OUT / "02-overlay-listed.png")
        log("run Modem / Net Run.HC twice and the echo tool")
        qmp.type_text('#include "C:/RUN.HC";\n', delay=0.06)
        com1.wait_for(b"NET_RUN1", 90.0)
        time.sleep(0.5)
        qmp.screendump(OUT / "03-net-run-first.png")
        status["shots"]["03-net-run-first"] = pil_check(OUT / "03-net-run-first.png")
        com1.wait_for(b"NET_RUN2", 90.0)
        time.sleep(2)
        qmp.screendump(OUT / "04-net-run-second.png")
        status["shots"]["04-net-run-second"] = pil_check(OUT / "04-net-run-second.png")
        qmp.type_text('#include "C:/ECHO.HC";\n', delay=0.06)
        com1.wait_for(b"NET_ECHO_END", 90.0)
        time.sleep(2)
        qmp.screendump(OUT / "05-net-echo.png")
        status["shots"]["05-net-echo"] = pil_check(OUT / "05-net-echo.png")
        qmp.type_text('Dir("C:/Tmp");\n', delay=0.06)
        time.sleep(5)
        qmp.screendump(OUT / "06-shell-usable.png")
        status["shots"]["06-shell-usable"] = pil_check(OUT / "06-shell-usable.png")
    except Exception as exc:
        status["errors"].append(f"{type(exc).__name__}: {exc}")
        log(f"ERROR {type(exc).__name__}: {exc}")
        try:
            if qmp:
                qmp.screendump(OUT / "99-error.png")
        except Exception:
            pass
    finally:
        try:
            if qmp:
                qmp.quit()
                time.sleep(2)
        except Exception:
            pass
        if proc is not None:
            for sig in (15, 9):
                if proc.poll() is not None:
                    break
                try:
                    proc.terminate()
                except Exception:
                    pass
                time.sleep(0.5)
                if proc.poll() is None:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        if com1 is not None:
            com1.stop()
        if stub is not None:
            for sig in (15, 9):
                if stub.poll() is not None:
                    break
                try:
                    stub.terminate()
                except Exception:
                    pass
                time.sleep(0.5)
                if stub.poll() is None:
                    try:
                        stub.kill()
                    except Exception:
                        pass

    for name in ("NET_STAGED", "NET_RUN1", "NET_RUN2", "NET_READY",
                 "NET_ECHO.RES", "NET_ECHO_DONE", "NET_ECHO_GUEST"):
        status["guest"][name] = read_guest_file(f"/Tmp/{name}")
    guest_echo = status["guest"].get("NET_ECHO_GUEST") or ""
    com1_text = com1.text() if com1 is not None else ""
    status["com1_markers"] = com1_text
    status["echo_ok"] = (
        status["guest"].get("NET_ECHO.RES") == "0"
        and status["guest"].get("NET_ECHO_DONE") == "ok"
        and "tx=HERMES-NET-ECHO-01" in guest_echo
        and "rx=HERMES-NET-ECHO-01" in guest_echo
    )
    stub_text = stub_log.read_text(encoding="utf-8", errors="replace") if stub_log.exists() else ""
    status["echo_bytes_both_ways"] = (
        "guest->stub" in stub_text
        and "stub->guest" in stub_text
        and "HERMES-NET-ECHO-01" in stub_text
    )
    status["checks"] = [
        {"name": "iso_sha256", "passed": True},
        {"name": "guest_run1", "passed": status["guest"].get("NET_RUN1") == "ok"},
        {"name": "guest_run2", "passed": status["guest"].get("NET_RUN2") == "ok"},
        {"name": "com1_run1_marker", "passed": "NET_RUN1" in com1_text},
        {"name": "com1_run2_marker", "passed": "NET_RUN2" in com1_text},
        {"name": "com1_echo_end_marker", "passed": "NET_ECHO_END" in com1_text},
        {"name": "guest_echo_result_zero", "passed": status["guest"].get("NET_ECHO.RES") == "0"},
        {"name": "guest_echo_done", "passed": status["guest"].get("NET_ECHO_DONE") == "ok"},
        {"name": "echo_bytes_both_ways", "passed": status["echo_bytes_both_ways"]},
        {"name": "all_png_640x480", "passed": all(v["size"] == [640, 480] for v in status["shots"].values() if isinstance(v, dict))},
        {"name": "all_png_palette_0_15", "passed": all(v["palette_0_15"] for v in status["shots"].values() if isinstance(v, dict))},
        {"name": "all_png_zero_off_palette", "passed": all(v["off_palette_pixels"] == 0 for v in status["shots"].values() if isinstance(v, dict))},
    ]
    (OUT / "run-status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    (OUT / "pil-checks.json").write_text(json.dumps(status["shots"], indent=2), encoding="utf-8")
    pil_lines = []
    for shot_name, rec in status["shots"].items():
        pil_lines.append(
            f"{shot_name}: size={rec['size']} palette_0_15={rec['palette_0_15']} "
            f"off_palette_pixels={rec['off_palette_pixels']} "
            f"indices={rec['mapped_palette_indices']} bbox={rec['bbox']}"
        )
    (OUT / "pil-checks.txt").write_text("\n".join(pil_lines) + "\n", encoding="utf-8")
    guest_summary = "\n".join(f"{k}: {v!r}" for k, v in status["guest"].items())
    with stub_log.open("a", encoding="utf-8") as fh:
        fh.write("\nGuest result files (read from the overlay FAT32 image):\n")
        fh.write(guest_summary + "\n")
        fh.write(f"\necho result: {status['guest'].get('NET_ECHO.RES')}\n")
        fh.write(f"echo bytes both ways: {status['echo_bytes_both_ways']}\n")
    for check in status["checks"]:
        log(f"check {check['name']}: {check['passed']}")
    return 0 if all(c["passed"] for c in status["checks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
