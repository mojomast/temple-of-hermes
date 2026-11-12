#!/usr/bin/env python3
"""Live-CD evidence: wrapper FAT at index 0, scratch at 1, content CD at 3."""
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
sys.path.insert(0, str(ROOT / "shots" / "bbs-auth-fix"))

from qemu_hermes import QMP, glyph_text  # noqa: E402
import make_overlay_fat32  # noqa: E402
from run_disk import INJECT_FILES, FakeRefresh, fat_offset, log, pil_save, wait_ocr  # noqa: E402


def build_wrapper(path: Path) -> int:
    path.write_bytes(make_overlay_fat32.build([]))
    offset = fat_offset(path)
    env = dict(os.environ, MTOOLS_SKIP_CHECK="1")
    dirs: set[str] = set()
    for rel in INJECT_FILES:
        parent = rel.rsplit("/", 1)[0]
        while parent and parent not in dirs:
            dirs.add(parent)
            parent = parent.rsplit("/", 1)[0]
    for rel in sorted(dirs, key=lambda p: (p.count("/"), p)):
        subprocess.check_call(["mmd", "-i", f"{path}@@{offset}", f"::/{rel}"], env=env)
    for rel in INJECT_FILES:
        subprocess.check_call([
            "mcopy", "-o", "-i", f"{path}@@{offset}",
            str(ROOT / rel), f"::/{rel}",
        ], env=env)
    marker = path.parent / "TOHINJ.MRK"
    marker.write_text("TOHINJ\n", encoding="ascii")
    subprocess.check_call([
        "mcopy", "-o", "-i", f"{path}@@{offset}",
        str(marker), "::/TOHINJ.MRK",
    ], env=env)
    return offset


def find_wrapper(h) -> str:
    for letter in "CDEFGH":
        status, data = h.request("stat", f"{letter}:/TOHINJ.MRK".encode(), timeout=5)
        if status == "ok" and b'"exists":1' in data:
            return letter
    raise RuntimeError("wrapper FAT not found")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True)
    ap.add_argument("--host-repo", required=True)
    ap.add_argument("--out", default=str(ROOT / "shots" / "bbs-auth-fix"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    run = Path("/tmp/opencode/bbs-auth-live")
    run.mkdir(parents=True, exist_ok=True)
    assets = Path(args.assets)

    wrapper = run / "wrapper.img"
    build_wrapper(wrapper)
    scratch = run / "scratch.qcow2"
    scratch.unlink(missing_ok=True)
    subprocess.check_call(["qemu-img", "create", "-f", "qcow2", str(scratch), "64M"])
    qmp, com1, com2 = run / "qmp.sock", run / "com1.sock", run / "com2.sock"
    for path in (qmp, com1, com2):
        path.unlink(missing_ok=True)
    argv = [
        "qemu-system-x86_64", "-name", "bbs-auth-live",
        "-machine", "pc,kernel-irqchip=off", "-accel", "tcg", "-cpu", "qemu64",
        "-m", "2G", "-smp", "1", "-vga", "std", "-display", "none", "-nic", "none",
        "-qmp", f"unix:{qmp},server=on,wait=off",
        "-serial", f"unix:{com1},server=on,wait=off",
        "-serial", f"unix:{com2},server=on,wait=off",
        "-cdrom", str(assets / "TempleOfHermes-0.1.3.ISO"),
        "-boot", "order=d,menu=on",
        "-drive", f"file={wrapper},format=raw,if=ide,index=0,media=disk",
        "-drive", f"file={scratch},format=qcow2,if=ide,index=1,media=disk",
        "-drive", f"file={assets / 'TempleOfHermes-0.1.3.ISO'},media=cdrom,format=raw,if=ide,index=3,readonly=on",
    ]
    qlog = (run / "qemu.log").open("wb")
    proc = subprocess.Popen(argv, stdout=qlog, stderr=qlog)
    server = relay = None
    serial = None
    try:
        q = QMP(qmp, timeout=60)
        wait_ocr(q, out, ["HERMES apps", "click an icon"], 240, "03-live-launcher")
        log("live launcher visible", out)
        sys.path.insert(0, str(ROOT / "shots" / "bbs-guest-fix"))
        from lab import Hrpc2

        h = Hrpc2(com1, timeout=30)
        try:
            status, _ = h.request("ping", b"", timeout=10)
            assert status == "ok"
            status, data = h.request(
                "eval", b'MountAuto(TRUE); "mounted\\n";', timeout=30
            )
            log(f"MountAuto(TRUE) {status}", out)
            letter = find_wrapper(h)
            assert letter in "CDEFGH"
            log(f"wrapper drive {letter}:", out)
            setup = (
                'HermesStateMakeRam; '
                'DirMk("B:/Tmp"); DirMk("B:/Tmp/Hermes"); DirMk("B:/Tmp/Hermes/HermesBBS"); '
                'if (IsFile("B:/Tmp/Hermes/HermesBBS/token.txt")) '
                'Del("B:/Tmp/Hermes/HermesBBS/token.txt"); "ok\\n";'
            )
            status, data = h.request("eval", setup.encode(), timeout=20)
            log(f"B: setup {status} {data[:80]!r}", out)
            launch = (
                f'User("Cd(\\"{letter}:/Hermes/Apps/HermesBBS\\");;'
                f'ExeFile(\\"{letter}:/Hermes/Apps/HermesBBS/Run.HC\\");\\n");'
            )
            status, data = h.request("eval", launch.encode(), timeout=20)
            log(f"launch eval {status} {data[:120]!r}", out)
        finally:
            h.close()

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
            "--port-file", str(port_file), "--log", str(out / "live-tls-server.log"),
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
            "--log", str(out / "live-modem.log"), "--modem-repo", str(ROOT),
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
        legacy = stage / "legacy-token.txt"
        legacy.write_text("expired.access.token.not.real\n", encoding="ascii")
        pushed = files.push(legacy, session.GUEST_TOKEN_LIVE)
        log(f"push expired fake token via={pushed.get('via')} ok={pushed.get('ok')}", out)
        assert pushed.get("ok") is True, pushed

        q.send_qcodes("f5")
        log("pressed F5 after expired token push", out)

        text, raw = wait_ocr(q, out, ["token_expired"], 90, "03-live-token-expired")
        pil_save(raw, out / "03-live-token-expired.png")
        (out / "03-live-token-expired.ocr.txt").write_text(text, encoding="utf-8")
        assert "token_expired" in text.lower()

        home = run / "tos-home"
        bbs_dir = home / "bbs"
        bbs_dir.mkdir(parents=True, exist_ok=True)
        bbs.persist_credentials(
            bbs_dir / "agent-fixture-agent.json",
            account="fixture-agent",
            access_token="stale.access.token.not.real",
            refresh_token=FakeRefresh.REFRESH,
            status="approved",
        )
        mode_file.write_text("fresh\n", encoding="ascii")
        body = session.bbs_push_guest_token(
            live_cd=True, client_factory=lambda: FakeRefresh(), push=files.push
        )
        log(f"host refresh+push ok={body.get('ok')} path={body.get('guest_path')}", out)
        assert body.get("pushed") is True
        assert "fixture.access.token" not in json.dumps(body)

        q.send_qcodes("f5")
        log("pressed F5", out)
        text, raw = wait_ocr(q, out, ["Connected to dest bbs"], 90, "04-live-connected")
        pil_save(raw, out / "04-live-connected.png")
        (out / "04-live-connected.ocr.txt").write_text(text, encoding="utf-8")
        assert "connected" in text.lower()
        assert "Fresh token accepted" in text or "THREADS" in text
        log("live evidence complete", out)
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
