#!/usr/bin/env python3
"""Sandbox-portable QEMU/QMP helpers for the Hermes art in-OS check.

TCG only. Paths are derived from this file, so the same script works on any host.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SHOTS = ROOT / "shots" / "hermes-art"
WORK = SHOTS / "raw"
QEMU = "qemu-system-x86_64"


class QMP:
    def __init__(self, path: Path, timeout: float = 60.0):
        self.path = path
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.buf = b""
        deadline = time.time() + timeout
        last: Exception | None = None
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

    def type_text(self, text: str, delay: float = 0.05) -> None:
        for ch in text:
            self.send_qcodes(*_qcodes_for(ch))
            time.sleep(delay)

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
    def __init__(self, path: Path, timeout: float = 60.0):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        deadline = time.time() + timeout
        last: Exception | None = None
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
        self.sock.sendall(data)

    def read_some(self, n: int = 4096, timeout: float = 0.2) -> bytes:
        self.sock.settimeout(timeout)
        try:
            return self.sock.recv(n)
        except socket.timeout:
            return b""

    def read_until(self, needle: bytes, timeout: float = 60.0) -> bytes:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if needle in self.buf:
                i = self.buf.index(needle) + len(needle)
                out, self.buf = self.buf[:i], self.buf[i:]
                return out
            chunk = self.read_some(timeout=min(1.0, max(0.05, deadline - time.time())))
            if chunk:
                self.buf += chunk
        raise TimeoutError(f"timeout waiting for {needle!r}, have {self.buf[-300:]!r}")


def start_vm(name: str, iso: Path, *, disks: list[tuple[Path, str]] | None = None,
             extra: list[str] | None = None, memory: str = "1G") -> dict[str, Any]:
    rundir = WORK / name
    rundir.mkdir(parents=True, exist_ok=True)
    for s in rundir.glob("*.sock"):
        s.unlink(missing_ok=True)
    qmp = rundir / "qmp.sock"
    com = rundir / "com1.sock"
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
        "-serial", f"unix:{com},server=on,wait=off",
        "-cdrom", str(iso),
        "-boot", "order=d,menu=off",
    ]
    for i, (path, fmt) in enumerate(disks or []):
        cmd += ["-drive", f"file={path},format={fmt},if=ide,index={i + 1},media=disk"]
    if extra:
        cmd += extra
    lf = log.open("ab")
    proc = subprocess.Popen(cmd, stdout=lf, stderr=lf)
    meta = {
        "name": name, "pid": proc.pid, "cmd": cmd,
        "qmp": str(qmp), "com1": str(com), "log": str(log),
        "started": time.time(),
    }
    (rundir / "meta.json").write_text(json.dumps(meta, indent=2))
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
