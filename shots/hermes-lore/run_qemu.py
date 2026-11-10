#!/usr/bin/env python3
"""Boot TinkerOS under QEMU TCG and screenshot the CODEX OF NOUS.

Portable by design: pass --iso or set TOH_TINKEROS_ISO. Three compact demo
sources (demo/DEMO1..3.HC) are pushed over COM1 into the live CD's writable B:
RAM drive and included. No host absolute paths, no hard-disk install, and
Once.HC is never touched.

The canonical, full lore lives in Hermes/Lore/. The demo sources are compact
on-screen renderings of the same entries because the live CD's compiler heap
is small; the demo keeps each include under ~1.6 KB.

All QEMU runs use TCG, no display, and no network:
  -accel tcg -display none -nic none -machine pc,kernel-irqchip=off
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import struct
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = HERE / "run"
TRANSCRIPT = HERE / "serial-transcript.txt"

DEMO_FILES = [
    ("demo/DEMO1.HC", "D1.HC"),
    ("demo/DEMO2.HC", "D2.HC"),
    ("demo/DEMO3.HC", "D3.HC"),
]


class QMP:
    def __init__(self, path: Path, timeout: float = 60.0):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.buf = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                self.sock.connect(str(path))
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError(f"QMP connect failed: {path}")
        self._read_obj()
        self.cmd("qmp_capabilities")

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
                raise RuntimeError("QMP closed")
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

    def shot(self, name: str) -> Path:
        dest = HERE / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.cmd("screendump", filename=str(dest), format="png")
        print(f"shot {dest}", flush=True)
        return dest

    def keys(self, *codes: str, hold: int = 100) -> None:
        self.cmd("send-key", keys=[{"type": "qcode", "data": c} for c in codes],
                 **{"hold-time": hold})

    def type(self, text: str, delay: float = 0.1) -> None:
        for ch in text:
            self.keys(*_qcodes(ch))
            time.sleep(delay)


class Serial:
    def __init__(self, path: Path, timeout: float = 60.0):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                self.sock.connect(str(path))
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError(f"serial connect failed: {path}")
        self.buf = b""

    def wait_mark(self, mark: bytes, timeout: float = 30.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if mark in self.buf:
                self.buf = self.buf.split(mark, 1)[1]
                return True
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                return False
            self.buf += chunk
        return mark in self.buf

    def send_length(self, n: int) -> None:
        self.sock.sendall(struct.pack("<I", n))

    def send_data(self, data: bytes, chunk: int = 32, delay: float = 0.01) -> None:
        for i in range(0, len(data), chunk):
            self.sock.sendall(data[i:i + chunk])
            time.sleep(delay)


_SHIFT = {
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
_PLAIN = {
    " ": "spc", "\n": "ret", "\t": "tab", "-": "minus", "=": "equal",
    "[": "bracket_left", "]": "bracket_right", "\\": "backslash",
    ";": "semicolon", "'": "apostrophe", ",": "comma", ".": "dot",
    "/": "slash", "`": "grave_accent",
}


def _qcodes(ch: str) -> list[str]:
    if ch in _SHIFT:
        return ["shift", _SHIFT[ch]]
    if ch in _PLAIN:
        return [_PLAIN[ch]]
    if "a" <= ch <= "z" or "0" <= ch <= "9":
        return [ch]
    raise ValueError(f"no qcode for {ch!r}")


def find_iso(arg: str | None) -> Path:
    if arg:
        p = Path(arg)
        if p.is_file():
            return p
        raise SystemExit(f"no ISO at {p}")
    env = os.environ.get("TOH_TINKEROS_ISO")
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates += [
        Path.cwd() / "TinkerOS_5.20-rc10.ISO",
        ROOT / "TinkerOS_5.20-rc10.ISO",
        Path("/tmp/toh-iso/TinkerOS_5.20-rc10.ISO"),
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise SystemExit("pass --iso or set TOH_TINKEROS_ISO")


def push_file(qmp: QMP, ser: Serial, rel: str, dest: str) -> int:
    data = (HERE / rel).read_bytes()
    print(f"push {rel} -> {dest} ({len(data)} bytes)", flush=True)
    qmp.type("I64 l,k;U8 *p;l=0;\n")
    time.sleep(1)
    qmp.type('CommPutS(1,"R");\n')
    time.sleep(1)
    qmp.type("l=CommGetChar(1,30000)|CommGetChar(1,30000)<<8;\n")
    time.sleep(1)
    qmp.type("l|=CommGetChar(1,30000)<<16;\n")
    time.sleep(1)
    qmp.type("l|=CommGetChar(1,30000)<<24;\n")
    time.sleep(1)
    if not ser.wait_mark(b"R", 20):
        raise RuntimeError(f"receiver did not announce R for {dest}")
    ser.send_length(len(data))
    time.sleep(2)
    qmp.type("p=MAlloc(l+1);\n")
    time.sleep(1)
    qmp.type('CommPutS(1,"D");\n')
    time.sleep(1)
    qmp.type("for(k=0;k<l;k++)p[k]=CommGetChar(1,30000);\n")
    time.sleep(1)
    if not ser.wait_mark(b"D", 20):
        raise RuntimeError(f"receiver did not announce D for {dest}")
    ser.send_data(data)
    time.sleep(3)
    qmp.type(f'FileWrite("{dest}",p,l);\n')
    time.sleep(1)
    qmp.type('CommPutS(1,"W");\n')
    time.sleep(1)
    if not ser.wait_mark(b"W", 60):
        raise RuntimeError(f"receiver did not announce W for {dest}")
    time.sleep(3)
    return len(data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iso")
    ap.add_argument("--probe", action="store_true",
                    help="boot and screenshot, do not push")
    ap.add_argument("--seconds", type=int, default=90)
    args = ap.parse_args()

    iso = find_iso(args.iso)
    RUN.mkdir(parents=True, exist_ok=True)
    qmp_path = RUN / "qmp.sock"
    com_path = RUN / "com1.sock"
    for p in (qmp_path, com_path, RUN / "qemu.pid"):
        if p.exists():
            p.unlink()

    cmd = [
        "qemu-system-x86_64",
        "-accel", "tcg",
        "-display", "none",
        "-nic", "none",
        "-machine", "pc,kernel-irqchip=off",
        "-m", "2G", "-smp", "1", "-vga", "std",
        "-boot", "d",
        "-cdrom", str(iso),
        "-serial", f"unix:{com_path},server=on,wait=off",
        "-qmp", f"unix:{qmp_path},server=on,wait=off",
        "-pidfile", str(RUN / "qemu.pid"),
    ]
    print(" ".join(cmd), flush=True)
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.STDOUT)
    qmp = None
    try:
        qmp = QMP(qmp_path)
        ser = Serial(com_path)
        if args.probe:
            for i in range(max(1, args.seconds // 10)):
                time.sleep(10)
                qmp.shot(f"probe-{i:02d}.png")
            return 0

        time.sleep(18)
        qmp.shot("00-boot.png")
        qmp.type("n\n")
        time.sleep(3)
        qmp.shot("01-after-install-prompt.png")
        qmp.type("n\n")
        time.sleep(3)
        qmp.shot("02-live-cd.png")

        qmp.type("CommInit;CommInit8n1(1,115200);\n")
        time.sleep(3)
        qmp.keys("esc")
        qmp.type("AutoComplete(0);\n")
        time.sleep(2)
        qmp.type('DirMk("B:/Home");\n')
        time.sleep(2)
        qmp.type('Cd("B:/Home");\n')
        time.sleep(2)

        sizes = []
        for rel, dest in DEMO_FILES:
            sizes.append(push_file(qmp, ser, rel, dest))

        qmp.type('DocClear;#include "D1.HC";\n')
        time.sleep(8)
        qmp.type('#include "D2.HC";\n')
        time.sleep(8)
        qmp.type('#include "D3.HC";\n')
        time.sleep(8)

        shots = [
            ("03-codex-index.png", "DocClear;Codex;\n"),
            ("04-codex-hermes.png", 'DocClear;Codex("hermes");\n'),
            ("05-codex-nous.png", 'DocClear;Codex("nous-research");\n'),
            ("06-motd.png", "DocClear;MOTD;\n"),
            ("07-oracle.png", "DocClear;Oracle;\n"),
            ("08-capybara.png", "DocClear;Capybara;\n"),
            ("09-caduceus.png", "DocClear;Caduceus;\n"),
            ("10-aletheia.png", "DocClear;Aletheia;\n"),
        ]
        for name, cmdline in shots:
            qmp.type(cmdline)
            time.sleep(7)
            qmp.shot(name)

        lines = [
            f"iso={iso.name}",
            "guest=live CD, writable B: RAM drive",
            "ack=R/D/W per file",
        ]
        for (rel, dest), n in zip(DEMO_FILES, sizes):
            lines.append(f"pushed {rel} -> B:/Home/{dest} ({n} bytes)")
        lines.append("includes=D1.HC D2.HC D3.HC")
        lines.append("shots=00-boot .. 10-aletheia")
        TRANSCRIPT.write_text("\n".join(lines) + "\n", encoding="ascii")
        return 0
    finally:
        if qmp is not None:
            try:
                qmp.cmd("quit")
            except Exception:
                pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
