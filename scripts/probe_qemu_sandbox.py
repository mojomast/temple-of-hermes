#!/usr/bin/env python3
"""Probe whether this sandbox can boot an ISO with QEMU under TCG.

Self-contained: standard library only, no box-specific paths. Boots the
in-tree Extras/TempleOS.ISO, captures a QMP screendump, shuts the VM down,
and reports QEMU version plus KVM usability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ISO = ROOT / "Extras" / "TempleOS.ISO"
DEFAULT_OUT = ROOT / "shots" / "hermes-qemu-probe"
QEMU = os.environ.get("QEMU_SYSTEM_X86_64", "qemu-system-x86_64")


class QMP:
    def __init__(self, path: Path, timeout: float = 30.0):
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
            raise RuntimeError(f"QMP connect failed: {path.name}: {last}")
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

    def screendump(self, dest: Path, fmt: str = "png") -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.cmd("screendump", filename=str(dest), format=fmt)
        deadline = time.time() + 10.0
        while time.time() < deadline:
            if dest.exists() and dest.stat().st_size > 0:
                return dest
            time.sleep(0.05)
        raise RuntimeError(f"screendump did not produce {dest.name}")

    def quit(self) -> None:
        try:
            self.cmd("quit")
        except Exception:
            pass


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def qemu_version(binary: str) -> str | None:
    try:
        out = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    first = (out.stdout or "").strip().splitlines()
    return first[0] if first else None


def kvm_status() -> dict[str, Any]:
    dev = Path("/dev/kvm")
    status: dict[str, Any] = {"path": "/dev/kvm", "exists": dev.exists()}
    if not dev.exists():
        status["usable"] = False
        status["reason"] = "device node absent"
        return status
    status["char_device"] = dev.is_char_device()
    try:
        fd = os.open(dev, os.O_RDWR)
        os.close(fd)
        status["usable"] = True
        status["reason"] = "opened read-write"
    except OSError as e:
        status["usable"] = False
        status["reason"] = f"open failed: {e.strerror or e}"
    return status


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ppm_header(data: bytes) -> tuple[int, int, int, int]:
    if not data.startswith(b"P6"):
        raise ValueError("not a P6 PPM")
    fields: list[int] = []
    i = 2
    while len(fields) < 3:
        while i < len(data) and data[i : i + 1].isspace():
            i += 1
        if data[i : i + 1] == b"#":
            while i < len(data) and data[i : i + 1] != b"\n":
                i += 1
            continue
        start = i
        while i < len(data) and not data[i : i + 1].isspace():
            i += 1
        fields.append(int(data[start:i]))
    if i < len(data) and data[i : i + 1].isspace():
        i += 1
    w, h, maxval = fields
    return w, h, maxval, i


def ppm_stats(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    w, h, maxval, off = _ppm_header(data)
    pixels = data[off:]
    stride = max(3, (len(pixels) // 3 // 20000) * 3)
    unique: set[tuple[int, int, int]] = set()
    nonblack = 0
    sampled = 0
    for i in range(0, len(pixels) - 2, stride):
        c = (pixels[i], pixels[i + 1], pixels[i + 2])
        sampled += 1
        if c != (0, 0, 0):
            nonblack += 1
        unique.add(c)
    return {
        "width": w,
        "height": h,
        "maxval": maxval,
        "bytes": len(data),
        "sampled_pixels": sampled,
        "unique_colors": len(unique),
        "nonblack_fraction": round(nonblack / sampled, 4) if sampled else 0.0,
    }


def png_info(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    ok = data.startswith(b"\x89PNG\r\n\x1a\n")
    info: dict[str, Any] = {"bytes": len(data), "signature_ok": ok}
    if ok and len(data) >= 24 and data[12:16] == b"IHDR":
        w, h = struct.unpack(">II", data[16:24])
        info["width"] = w
        info["height"] = h
    return info


def build_cmd(
    binary: str,
    iso: Path,
    qmp: Path,
    memory: str,
    boot: str,
) -> list[str]:
    return [
        binary,
        "-name", "hermes-qemu-probe",
        "-machine", "pc,kernel-irqchip=off",
        "-accel", "tcg",
        "-cpu", "qemu64",
        "-m", memory,
        "-smp", "1",
        "-vga", "std",
        "-display", "none",
        "-nic", "none",
        "-qmp", f"unix:{qmp},server=on,wait=off",
        "-cdrom", str(iso),
        "-boot", f"order={boot},menu=on",
        "-no-reboot",
    ]


def stop_vm(proc: subprocess.Popen[bytes], qmp: QMP | None) -> dict[str, Any]:
    if qmp:
        qmp.quit()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    return {"pid": proc.pid, "returncode": proc.returncode, "stopped": proc.poll() is not None}


def probe(
    iso: Path,
    out: Path,
    memory: str = "1G",
    boot: str = "d",
    settle: float = 25.0,
    timeout: float = 150.0,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "iso": rel(iso),
        "memory": memory,
        "accel": "tcg",
        "machine": "pc,kernel-irqchip=off",
        "boot_order": boot,
    }

    binary = shutil.which(QEMU)
    report["qemu_binary"] = binary
    report["qemu_version"] = qemu_version(binary) if binary else None
    report["kvm"] = kvm_status()
    report["qemu_installed"] = bool(binary)
    if not binary:
        report["ok"] = False
        report["error"] = f"{QEMU} not found on PATH"
        return report

    if not iso.is_file():
        report["ok"] = False
        report["error"] = f"ISO not found: {rel(iso)}"
        return report
    report["iso_bytes"] = iso.stat().st_size
    report["iso_sha256"] = sha256_file(iso)

    out.mkdir(parents=True, exist_ok=True)
    rundir = out / "run"
    rundir.mkdir(parents=True, exist_ok=True)
    qmp_path = rundir / "qmp.sock"
    qmp_path.unlink(missing_ok=True)
    log_path = out / "qemu.log"
    png_path = out / "boot.png"
    ppm_path = rundir / "boot.ppm"

    cmd = build_cmd(binary, iso, qmp_path, memory, boot)
    report["cmd"] = [arg.replace(str(ROOT), ".") for arg in cmd]
    started = time.time()
    with log_path.open("wb") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    report["pid"] = proc.pid

    qmp: QMP | None = None
    try:
        qmp = QMP(qmp_path, timeout=30.0)
        deadline = started + timeout
        time.sleep(min(settle, max(0.0, deadline - time.time())))
        stats: dict[str, Any] = {}
        while True:
            qmp.screendump(ppm_path, fmt="ppm")
            stats = ppm_stats(ppm_path)
            content_ok = stats["nonblack_fraction"] >= 0.02 and stats["unique_colors"] >= 3
            if content_ok:
                break
            if time.time() >= deadline:
                raise RuntimeError(f"guest framebuffer stayed blank: {stats}")
            time.sleep(2.0)
        qmp.screendump(png_path, fmt="png")
        report["boot_seconds"] = round(time.time() - started, 2)
        report["framebuffer"] = stats
        report["screenshot"] = png_info(png_path)
        report["screenshot"]["path"] = rel(png_path)
        report["ok"] = report["screenshot"]["signature_ok"] and report["screenshot"]["bytes"] > 1024
    except Exception as e:
        report["ok"] = False
        report["error"] = f"{type(e).__name__}: {e}"
    finally:
        report["shutdown"] = stop_vm(proc, qmp)
        if qmp:
            qmp.close()
        shutil.rmtree(rundir, ignore_errors=True)

    report["elapsed_seconds"] = round(time.time() - started, 2)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--iso", type=Path, default=DEFAULT_ISO)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--memory", default="1G")
    ap.add_argument("--boot", default="d")
    ap.add_argument("--settle", type=float, default=25.0)
    ap.add_argument("--timeout", type=float, default=150.0)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args(argv)

    report = probe(
        iso=args.iso,
        out=args.out,
        memory=args.memory,
        boot=args.boot,
        settle=args.settle,
        timeout=args.timeout,
    )
    dest = args.json_out or (args.out / "probe.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
