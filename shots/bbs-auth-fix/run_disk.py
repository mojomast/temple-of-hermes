#!/usr/bin/env python3
"""Disk-boot evidence: token_expired status then a fresh-token Connected path."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from qemu_hermes import QMP, glyph_text  # noqa: E402


def log(msg: str, out: Path) -> None:
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with (out / "run.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def pil_save(src: Path, dst: Path) -> dict:
    im = Image.open(src).convert("RGB")
    if im.size != (640, 480):
        im = im.resize((640, 480), Image.Resampling.NEAREST)
    q = im.quantize(colors=16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    idx = set(q.getdata())
    assert q.size == (640, 480), q.size
    assert max(idx) <= 15, idx
    q.save(dst)
    return {"size": q.size, "mode": q.mode, "unique": len(idx),
            "max_index": max(idx), "off_palette": sum(1 for i in idx if i > 15)}


def shot(q: QMP, dst: Path, out: Path, name: str) -> str:
    raw = out / "_raw" / f"{name}.png"
    raw.parent.mkdir(parents=True, exist_ok=True)
    q.screendump(raw)
    info = pil_save(raw, dst)
    text = glyph_text(dst)
    dst.with_suffix(".ocr.txt").write_text(text, encoding="utf-8")
    log(f"shot {name} {info}", out)
    log("OCR " + text.replace("\n", " | ")[:400], out)
    return text


def wait_ocr(q: QMP, out: Path, needles: list[str], timeout: float, name: str) -> tuple[str, Path]:
    deadline = time.time() + timeout
    n = 0
    last = ""
    while time.time() < deadline:
        n += 1
        tmp = out / "_raw" / f"{name}-poll-{n:03d}.png"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        q.screendump(tmp)
        try:
            last = glyph_text(tmp)
        except Exception as exc:
            last = f"<ocr {type(exc).__name__}>"
        low = last.lower()
        if any(needle.lower() in low for needle in needles):
            return last, tmp
        time.sleep(2)
    raise TimeoutError(f"{name}: wanted {needles}, last={last[-300:]!r}")


INJECT_FILES = [
    "Hermes/Net/Modem.HC",
    "Hermes/Net/Glbls.HC",
    "Hermes/Net/Protocol.HC",
    "Hermes/Net/Load.HC",
    "Hermes/Apps/Common/Paths.HC",
    "Hermes/Apps/Common/Icons.HC",
    "Hermes/Apps/Launcher/Load.HC",
    "Hermes/Apps/Launcher/RunFile.HC",
    "Hermes/Apps/Registry.HC",
    "Adam/Hermes/Protocol.HC",
    "Hermes/Apps/HermesBBS/BBS.HC",
    "Hermes/Apps/HermesBBS/Load.HC",
    "Hermes/Apps/HermesBBS/Run.HC",
]


def fat_offset(disk: Path) -> int:
    with disk.open("rb") as fh:
        mbr = fh.read(512)
    start_lba = int.from_bytes(mbr[446 + 8:446 + 12], "little")
    assert start_lba > 0, start_lba
    return start_lba * 512


def inject(disk: Path) -> None:
    offset = fat_offset(disk)
    env = dict(os.environ, MTOOLS_SKIP_CHECK="1")
    for rel in INJECT_FILES:
        subprocess.check_call([
            "mcopy", "-o", "-i", f"{disk}@@{offset}",
            str(ROOT / rel), f"::/{rel}",
        ], env=env)


class FakeRefresh:
    ACCESS = "fixture.access.token"
    REFRESH = "fixture.refresh.token"

    def connect(self):
        return self

    def auth_refresh(self, token):
        return {
            "access_token": self.ACCESS,
            "refresh_token": self.REFRESH,
            "account": {"account": "fixture-agent", "kind": "agent"},
        }

    def close(self):
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True)
    ap.add_argument("--host-repo", required=True)
    ap.add_argument("--out", default=str(ROOT / "shots" / "bbs-auth-fix"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    run = Path("/tmp/opencode/bbs-auth-disk")
    run.mkdir(parents=True, exist_ok=True)
    assets = Path(args.assets)

    disk = run / "disk.raw"
    disk.unlink(missing_ok=True)
    subprocess.check_call([
        "qemu-img", "convert", "-O", "raw",
        str(assets / "TempleOfHermes-0.1.3-disk.qcow2"), str(disk),
    ])
    inject(disk)
    qmp, com1, com2 = run / "qmp.sock", run / "com1.sock", run / "com2.sock"
    for path in (qmp, com1, com2):
        path.unlink(missing_ok=True)
    argv = [
        "qemu-system-x86_64", "-name", "bbs-auth-disk",
        "-machine", "pc,kernel-irqchip=off", "-accel", "tcg", "-cpu", "qemu64",
        "-m", "2G", "-smp", "1", "-vga", "std", "-display", "none", "-nic", "none",
        "-qmp", f"unix:{qmp},server=on,wait=off",
        "-serial", f"unix:{com1},server=on,wait=off",
        "-serial", f"unix:{com2},server=on,wait=off",
        "-boot", "order=c,menu=on",
        "-drive", f"file={disk},format=raw,if=ide,index=0,media=disk",
        "-drive", f"file={assets / 'TempleOfHermes-0.1.3.ISO'},media=cdrom,format=raw,if=ide,index=3,readonly=on",
    ]
    qlog = (run / "qemu.log").open("wb")
    proc = subprocess.Popen(argv, stdout=qlog, stderr=qlog)
    server = relay = None
    serial = None
    try:
        q = QMP(qmp, timeout=60)
        wait_ocr(q, out, ["HERMES apps", "click an icon"], 180, "00-launcher")
        log("launcher visible", out)

        cert, key = run / "cert.pem", run / "key.pem"
        if not cert.exists():
            subprocess.check_call([
                "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                "-keyout", str(key), "-out", str(cert), "-days", "2",
                "-subj", "/CN=localhost",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        mode_file = run / "mode.txt"
        token_file = run / "expected-token.txt"
        mode_file.write_text("expired\n", encoding="ascii")
        token_file.write_text(FakeRefresh.ACCESS + "\n", encoding="ascii")
        port_file = run / "tls-port.txt"
        port_file.unlink(missing_ok=True)
        server = subprocess.Popen([
            sys.executable, str(Path(__file__).with_name("loopback_hbbs.py")),
            "--port-file", str(port_file), "--log", str(out / "disk-tls-server.log"),
            "--cert", str(cert), "--key", str(key),
            "--mode-file", str(mode_file), "--token-file", str(token_file),
        ])
        deadline = time.time() + 10
        while not port_file.exists() and time.time() < deadline:
            time.sleep(0.05)
        port = int(port_file.read_text())
        relay = subprocess.Popen([
            sys.executable, str(Path(__file__).with_name("relay.py")),
            "--serial", str(com2), "--tls-port", str(port),
            "--log", str(out / "disk-modem.log"), "--modem-repo", str(ROOT),
        ])
        time.sleep(0.5)

        sys.path.insert(0, args.host_repo)
        os.environ["TEMPLEOS_HOME"] = str(run / "tos-home")
        from templeos import bbs, files, session
        from templeos.serial import SerialPort

        serial = SerialPort()
        serial.open(com1, timeout_s=5)
        files.bind_serial(serial)

        stage = run / "tos-home" / "exchange"
        stage.mkdir(parents=True, exist_ok=True)
        stat = files.list_guest("C:/Hermes/Apps/HermesBBS/")
        names = [e.get("name") for e in stat.get("entries", [])]
        assert "BBS.HC" in names, names

        legacy = stage / "legacy-token.txt"
        legacy.write_text("expired.access.token.not.real\n", encoding="ascii")
        pushed = files.push(legacy, session.GUEST_TOKEN_DISK)
        log(f"push expired fake token via={pushed.get('via')} ok={pushed.get('ok')}", out)
        assert pushed.get("ok") is True, pushed

        q.type_text("s", delay=0.1)
        log("pressed S for BBS", out)
        text, raw = wait_ocr(q, out, ["token_expired"], 45, "01-disk-token-expired")
        pil_save(raw, out / "01-disk-token-expired.png")
        (out / "01-disk-token-expired.ocr.txt").write_text(text, encoding="utf-8")
        assert "token_expired" in text.lower()

        home = run / "tos-home"
        bbs_dir = home / "bbs"
        bbs_dir.mkdir(parents=True, exist_ok=True)
        agent_path = bbs_dir / "agent-fixture-agent.json"
        bbs.persist_credentials(
            agent_path,
            account="fixture-agent",
            access_token="stale.access.token.not.real",
            refresh_token=FakeRefresh.REFRESH,
            status="approved",
        )
        mode_file.write_text("fresh\n", encoding="ascii")
        body = session.bbs_push_guest_token(
            client_factory=lambda: FakeRefresh(), push=files.push
        )
        log(f"host refresh+push ok={body.get('ok')} path={body.get('guest_path')}", out)
        assert body.get("pushed") is True
        assert "fixture.access.token" not in json.dumps(body)

        q.send_qcodes("f5")
        log("pressed F5", out)
        text, raw = wait_ocr(q, out, ["Connected to dest bbs"], 45, "02-disk-connected")
        pil_save(raw, out / "02-disk-connected.png")
        (out / "02-disk-connected.ocr.txt").write_text(text, encoding="utf-8")
        assert "connected" in text.lower()
        assert "Fresh token accepted" in text or "THREADS" in text
        log("disk evidence complete", out)
        q.quit()
    finally:
        if serial is not None:
            try:
                serial.close()
            except Exception:
                pass
        for child in (relay, server):
            if child is not None:
                try:
                    child.terminate()
                    child.wait(timeout=5)
                except Exception:
                    try:
                        child.kill()
                    except Exception:
                        pass
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        qlog.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
