#!/usr/bin/env python3
"""QEMU + QMP + COM1 helpers for building and smoking THE TEMPLE OF HERMES."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "run"
SHOTS = ROOT / "shots"
STOCK_ISO = Path(
    os.environ.get("TOH_TINKEROS_ISO")
    or (ROOT / "run" / "TinkerOS_5.20-rc10.ISO")
)
QEMU = "qemu-system-x86_64"



class QMP:
    def __init__(self, path: Path, timeout: float = 30.0):
        self.path = path
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.buf = b""
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            try:
                self.sock.connect(str(path))
                break
            except OSError as e:
                last = e
                time.sleep(0.1)
        else:
            raise RuntimeError(f"QMP connect failed: {path}: {last}")
        self._read_obj()
        self.cmd("qmp_capabilities")

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def _read_obj(self) -> dict[str, Any]:
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

    def cmd(self, execute: str, **arguments: Any) -> dict[str, Any]:
        msg: dict[str, Any] = {"execute": execute}
        if arguments:
            msg["arguments"] = arguments
        self.sock.sendall((json.dumps(msg) + "\n").encode())
        resp = self._read_obj()
        if "error" in resp:
            raise RuntimeError(f"QMP {execute} error: {resp['error']}")
        return resp

    def hmp(self, command: str) -> str:
        resp = self.cmd("human-monitor-command", **{"command-line": command})
        return str(resp.get("return", ""))

    def screendump(self, dest: Path, fmt: str = "png") -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.cmd("screendump", filename=str(dest), format=fmt)
        return dest

    def send_qcodes(self, *codes: str, hold: int = 80) -> None:
        keys = [{"type": "qcode", "data": c} for c in codes]
        self.cmd("send-key", keys=keys, **{"hold-time": hold})

    def type_text(self, text: str, delay: float = 0.06) -> None:
        for ch in text:
            self.send_qcodes(*_qcodes_for(ch))
            time.sleep(delay)

    def mouse_move_rel(self, dx: int, dy: int) -> None:
        self.hmp(f"mouse_move {int(dx)} {int(dy)}")

    def mouse_button(self, down: bool) -> None:
        self.hmp(f"mouse_button {1 if down else 0}")

    def mouse_home(self) -> None:
        for _ in range(3):
            self.mouse_move_rel(-900, -900)
            time.sleep(0.03)

    def mouse_click_at(self, x: int, y: int) -> None:
        """Absolute VMMouse click in 640x480 guest pixels (QMP input-send-event)."""
        ax = int(x * 32767 / 639)
        ay = int(y * 32767 / 479)
        self.cmd("input-send-event", events=[
            {"type": "abs", "data": {"axis": "x", "value": ax}},
            {"type": "abs", "data": {"axis": "y", "value": ay}},
        ])
        time.sleep(0.25)
        self.cmd("input-send-event",
                 events=[{"type": "btn", "data": {"down": True, "button": "left"}}])
        time.sleep(0.20)
        self.cmd("input-send-event",
                 events=[{"type": "btn", "data": {"down": False, "button": "left"}}])
        time.sleep(0.10)

    def quit(self) -> None:
        try:
            self.cmd("quit")
        except Exception:
            pass


_SHIFT = {
    "A": "a", "B": "b", "C": "c", "D": "d", "E": "e", "F": "f", "G": "g",
    "H": "h", "I": "i", "J": "j", "K": "k", "L": "l", "M": "m", "N": "n",
    "O": "o", "P": "p", "Q": "q", "R": "r", "S": "s", "T": "t", "U": "u",
    "V": "v", "W": "w", "X": "x", "Y": "y", "Z": "z",
    '"': "apostrophe",
    ":": "semicolon",
    "_": "minus",
    "+": "equal",
    "{": "bracket_left",
    "}": "bracket_right",
    "|": "backslash",
    "<": "comma",
    ">": "dot",
    "?": "slash",
    "!": "1", "@": "2", "#": "3", "$": "4", "%": "5",
    "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
    "~": "grave_accent",
}

_PLAIN = {
    " ": "spc",
    "\n": "ret",
    "\t": "tab",
    "-": "minus",
    "=": "equal",
    "[": "bracket_left",
    "]": "bracket_right",
    "\\": "backslash",
    ";": "semicolon",
    "'": "apostrophe",
    ",": "comma",
    ".": "dot",
    "/": "slash",
    "`": "grave_accent",
}


def _qcodes_for(ch: str) -> list[str]:
    if ch in _SHIFT:
        return ["shift", _SHIFT[ch]]
    if ch in _PLAIN:
        return [_PLAIN[ch]]
    if "a" <= ch <= "z" or "0" <= ch <= "9":
        return [ch]
    raise ValueError(f"no qcode for {ch!r}")


class Serial:
    def __init__(self, path: Path, timeout: float = 30.0, log: Path | None = None):
        self.path = path
        self.log = log
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            try:
                self.sock.connect(str(path))
                break
            except OSError as e:
                last = e
                time.sleep(0.1)
        else:
            raise RuntimeError(f"serial connect failed: {path}: {last}")
        self.buf = b""

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def write(self, data: bytes) -> None:
        if self.log:
            with self.log.open("ab") as f:
                f.write(data)
        self.sock.sendall(data)

    def read_some(self, n: int = 4096, timeout: float = 0.2) -> bytes:
        self.sock.settimeout(timeout)
        try:
            chunk = self.sock.recv(n)
        except socket.timeout:
            return b""
        if self.log and chunk:
            with self.log.open("ab") as f:
                f.write(b"<< " + chunk)
        return chunk or b""

    def read_until(self, needle: bytes, timeout: float = 30.0) -> bytes:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if needle in self.buf:
                i = self.buf.index(needle) + len(needle)
                out, self.buf = self.buf[:i], self.buf[i:]
                return out
            chunk = self.read_some(timeout=min(1.0, max(0.05, deadline - time.time())))
            if chunk:
                self.buf += chunk
        raise TimeoutError(f"timeout waiting for {needle!r}, have {self.buf[-200:]!r}")

    def drain(self, seconds: float = 0.3) -> bytes:
        deadline = time.time() + seconds
        out = b""
        while time.time() < deadline:
            chunk = self.read_some(timeout=0.1)
            if chunk:
                out += chunk
                self.buf += chunk
        return out


_FONT_CACHE: list[int] | None = None


def _font_glyphs() -> list[int]:
    """Parse Kernel/FontStd.HC (8x8 bitmaps) into 64-bit cell masks.

    TempleOS stores each glyph as a U64: low byte is the top row and bit 0 is
    the leftmost pixel.
    """
    global _FONT_CACHE
    if _FONT_CACHE is not None:
        return _FONT_CACHE
    import re
    import struct

    raw = (ROOT / "Kernel" / "FontStd.HC").read_bytes().decode("latin-1")
    body = raw.split("{", 1)[1].split("}", 1)[0]
    vals = [int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]{16})", body)]
    masks: list[int] = []
    for v in vals:
        b = struct.pack("<Q", v)
        m = 0
        for y, byte in enumerate(b):
            for x in range(8):
                if (byte >> x) & 1:
                    m |= 1 << (y * 8 + x)
        masks.append(m)
    _FONT_CACHE = masks
    return masks


def _ocr_at(im, ox: int, oy: int, min_score: int = 58) -> str:
    glyphs = _font_glyphs()
    px = im.load()
    w, h = im.size
    full = (1 << 64) - 1
    lines: list[str] = []
    for cy in range((h - oy) // 8):
        line: list[str] = []
        for cx in range((w - ox) // 8):
            x0 = cx * 8 + ox
            y0 = cy * 8 + oy
            counts: dict[tuple[int, int, int], int] = {}
            for y in range(8):
                for x in range(8):
                    c = px[x0 + x, y0 + y]
                    counts[c] = counts.get(c, 0) + 1
            bg = max(counts, key=counts.get)
            m = 0
            for y in range(8):
                for x in range(8):
                    if px[x0 + x, y0 + y] != bg:
                        m |= 1 << (y * 8 + x)
            if m == 0:
                line.append(" ")
                continue
            best = 0
            best_score = -1
            best_inv = -1
            best_inv_ch = 0
            lim = min(len(glyphs), 126)
            for i in range(32, lim):
                sc = 64 - (m ^ glyphs[i]).bit_count()
                if sc > best_score:
                    best_score = sc
                    best = i
                si = 64 - (m ^ full ^ glyphs[i]).bit_count()
                if si > best_inv:
                    best_inv = si
                    best_inv_ch = i
            if best_score >= min_score:
                line.append(chr(best))
            elif best_inv >= min_score:
                line.append(chr(best_inv_ch))
            else:
                line.append("?")
        lines.append("".join(line).rstrip())
    return "\n".join(lines)


def ocr_variants(image_path: Path) -> list[str]:
    """OCR the screen at each 8-pixel horizontal offset.

    TempleOS GrPrint can start a text run at any x, so one fixed grid is not
    enough.  Vertical cell rows are 8-pixel aligned on the screens we read.
    """
    im = Image.open(image_path).convert("RGB")
    return [_ocr_at(im, ox, 0) for ox in range(8)]


def glyph_text(image_path: Path) -> str:
    """Best-effort OCR text for one screendump (no external OCR package)."""
    variants = ocr_variants(image_path)
    def confident(text: str) -> int:
        return sum(1 for ch in text if ch not in " ?")
    return max(variants, key=confident)


def wait_for_text(
    qmp: QMP,
    shots: Path,
    needle: str,
    timeout: float = 600.0,
    interval: float = 8.0,
    prefix: str = "wait",
) -> str:
    """Poll screendumps until glyph OCR contains needle (case-insensitive)."""
    shots.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout
    n = 0
    last = ""
    needle_l = needle.lower()
    while time.time() < deadline:
        n += 1
        dest = shots / f"{prefix}-{n:03d}.png"
        qmp.screendump(dest)
        try:
            variants = ocr_variants(dest)
            last = max(variants, key=lambda t: sum(1 for c in t if c not in " ?"))
        except Exception as e:
            variants = []
            last = f"<ocr error: {e}>"
        for text in variants:
            if needle_l in text.lower():
                return text
        print(f"[wait] {prefix} #{n} needle={needle!r} got={last[:240]!r}", flush=True)
        time.sleep(interval)
    raise TimeoutError(f"timed out waiting for {needle!r}; last text:\n{last}")


def start_vm(
    name: str,
    iso: Path,
    disk: Path | None,
    memory: str = "2G",
    boot: str = "d",
    extra: list[str] | None = None,
    serial2: bool = False,
) -> dict[str, Any]:
    rundir = RUN / name
    rundir.mkdir(parents=True, exist_ok=True)
    for s in rundir.glob("*.sock"):
        s.unlink(missing_ok=True)
    qmp = rundir / "qmp.sock"
    vnc = rundir / "vnc.sock"
    com = rundir / "com1.sock"
    com2 = rundir / "com2.sock"
    log = rundir / "qemu.log"
    cmd = [
        QEMU,
        "-name", name,
        "-machine", "pc,kernel-irqchip=off",
        "-accel", "tcg",
        "-cpu", "qemu64",
        "-m", memory,
        "-smp", "1",
        "-vga", "std",
        "-display", "none",
        "-nic", "none",
        "-qmp", f"unix:{qmp},server=on,wait=off",
        "-vnc", f"unix:{vnc}",
        "-serial", f"unix:{com},server=on,wait=off",
        "-cdrom", str(iso),
        "-boot", f"order={boot},menu=on",
    ]
    if serial2:
        cmd += ["-serial", f"unix:{com2},server=on,wait=off"]
    if disk is not None:
        cmd += ["-drive", f"file={disk},format=qcow2,if=ide,index=0,media=disk"]
    if extra:
        cmd += extra
    lf = log.open("ab")
    proc = subprocess.Popen(cmd, stdout=lf, stderr=lf)
    meta = {
        "name": name,
        "pid": proc.pid,
        "cmd": cmd,
        "qmp": str(qmp),
        "vnc": str(vnc),
        "com1": str(com),
        "com2": str(com2),
        "disk": str(disk) if disk else None,
        "iso": str(iso),
        "log": str(log),
        "started": time.time(),
    }
    (rundir / "meta.json").write_text(json.dumps(meta, indent=2))
    (rundir / "pid").write_text(str(proc.pid))
    return meta


def stop_vm(meta: dict[str, Any], qmp: QMP | None = None) -> None:
    if qmp:
        qmp.quit()
        time.sleep(1)
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
