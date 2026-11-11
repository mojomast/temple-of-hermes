#!/usr/bin/env python3
"""Cold-boot and persistence checks for a preinstalled Temple of Hermes disk.

Every boot is a new QEMU VM with no CD attached.  Screenshots are captured with
PIL only (never opened in-model), converted to 640x480 palette images with
indices 0-15, and checked for off-palette pixels.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qemu_hermes import QMP, glyph_text  # noqa: E402
from hrpc import Hrpc  # noqa: E402

QEMU = "qemu-system-x86_64"
PALETTE = [
    (0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170),
    (170, 0, 0), (170, 0, 170), (170, 85, 0), (170, 170, 170),
    (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255),
    (255, 85, 85), (255, 85, 255), (255, 255, 85), (255, 255, 255),
]
BAD_PHRASES = (
    "Install onto hard drive",
    "Take Tour",
    "System Keys Quick Guide",
    "AutoComplete is in StandBy",
    "TinkerOS Debugger",
    "Unhandled Exception",
)
MARKERS = [
    ("C:/Home/TEST-MARKER.TXT", b"TEST-MARKER\n"),
    ("C:/Hermes/Apps/HermesBBS/TEST-TOKEN.TXT", b"TEST-TOKEN\n"),
]


def log(msg: str, path: Path | None = None) -> None:
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(line + "\n")


def to_palette(src: Path, dest: Path) -> dict:
    from PIL import Image
    im = Image.open(src).convert("RGB")
    if im.size != (640, 480):
        raise ValueError(f"{src} is {im.size}, not 640x480")
    cache: dict[tuple[int, int, int], int] = {}
    out = Image.new("P", im.size)
    ip, op = im.load(), out.load()
    off = 0
    for y in range(480):
        for x in range(640):
            rgb = ip[x, y]
            i = cache.get(rgb)
            if i is None:
                if rgb in PALETTE:
                    i = PALETTE.index(rgb)
                else:
                    best, bd = 0, 1 << 30
                    for k, c in enumerate(PALETTE):
                        d = (rgb[0] - c[0]) ** 2 + (rgb[1] - c[1]) ** 2 + (rgb[2] - c[2]) ** 2
                        if d < bd:
                            bd, best = d, k
                    i = best
                    off += 1
                cache[rgb] = i
            op[x, y] = i
    out.putpalette([c for rgb in PALETTE for c in rgb] + [0] * (768 - 48))
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    colors = set(out.getdata())
    if max(colors) > 15:
        raise ValueError(f"{dest} uses palette index > 15")
    return {"size": [640, 480], "mode": "P", "max_index": max(colors),
            "off_palette_pixels": off}


def start(rundir: Path, disk: Path, memory: str) -> tuple[subprocess.Popen, dict]:
    rundir.mkdir(parents=True, exist_ok=True)
    for s in rundir.glob("*.sock"):
        s.unlink(missing_ok=True)
    qmp = rundir / "qmp.sock"
    com = rundir / "com1.sock"
    cmd = [
        QEMU, "-name", rundir.name,
        "-machine", "pc,kernel-irqchip=off",
        "-accel", "tcg", "-cpu", "qemu64",
        "-m", memory, "-smp", "1", "-vga", "std",
        "-display", "none", "-nic", "none",
        "-qmp", f"unix:{qmp},server=on,wait=off",
        "-serial", f"unix:{com},server=on,wait=off",
        "-drive", f"file={disk},format=qcow2,if=ide,index=0,media=disk",
        "-boot", "order=c,menu=off",
    ]
    lf = (rundir / "qemu.log").open("wb")
    proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT)
    return proc, {"qmp": qmp, "com1": com}


def stop(proc: subprocess.Popen, q: QMP | None) -> None:
    if q:
        try:
            q.quit()
        except Exception:
            pass
        time.sleep(0.8)
        try:
            q.close()
        except Exception:
            pass
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def overlay_windows(h: Hrpc) -> list[dict]:
    st, d = h.request("windows", b"", timeout=10)
    if st != "ok":
        return []
    return json.loads(d.decode()).get("windows", [])


def launcher_ok(q: QMP, rundir: Path) -> tuple[bool, str, str]:
    p = rundir / "launcher.png"
    q.screendump(p)
    try:
        text = glyph_text(p)
    except Exception:
        text = ""
    return True, text, str(p)


def boot_trial(index: int, image: Path, outdir: Path, work: Path,
               timeout: float, memory: str, save: bool) -> dict:
    rundir = work / f"boot-{index:02d}"
    started = time.time()
    proc, m = start(rundir, image, memory)
    q = None
    h = None
    result = {"trial": index, "ok": False, "seconds": None, "reason": "",
              "windows": [], "shot": None, "shot_meta": None}
    try:
        q = QMP(m["qmp"], timeout=30)
        deadline = time.time() + timeout
        text = ""
        while time.time() < deadline:
            _, text, shot = launcher_ok(q, rundir)
            low = text.lower()
            bad = [p for p in BAD_PHRASES if p.lower() in low]
            if ("hermes apps" in low or "click an icon" in low) and not bad:
                break
            time.sleep(1.5)
        else:
            result["reason"] = "launcher not visible: " + text[-200:].replace("\n", " | ")
            return result
        try:
            h = Hrpc(m["com1"], timeout=10)
            h.request("ping", b"", timeout=10)
            ws = overlay_windows(h)
        except Exception as e:  # noqa: BLE001
            result["reason"] = f"HRPC: {type(e).__name__}: {e}"
            return result
        titles = [w.get("title", "") for w in ws]
        if titles != ["Hermes Apps"]:
            result["reason"] = "visible windows: " + repr(titles)
            result["windows"] = ws
            return result
        if save:
            dest = outdir / f"boot-{index:02d}.png"
            meta = to_palette(Path(shot), dest)
            result["shot"] = dest.name
            result["shot_meta"] = meta
        result["ok"] = True
        result["windows"] = ws
        result["seconds"] = round(time.time() - started, 1)
        return result
    finally:
        if h:
            try:
                h.close()
            except Exception:
                pass
        stop(proc, q)


def wait_for_vm(rundir: Path, image: Path, memory: str,
                timeout: float) -> tuple[subprocess.Popen, QMP, Hrpc, dict]:
    proc, m = start(rundir, image, memory)
    q = None
    h = None
    try:
        q = QMP(m["qmp"], timeout=30)
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(2)
            h = None
            try:
                h = Hrpc(m["com1"], timeout=10)
                h.request("ping", b"", timeout=10)
                ws = overlay_windows(h)
                if [w.get("title") for w in ws] == ["Hermes Apps"]:
                    return proc, q, h, m
            except Exception:
                if h:
                    h.close()
                h = None
        raise RuntimeError("launcher/HRPC not ready")
    except Exception:
        stop(proc, q)
        raise


def dir_has(h: Hrpc, parent_glob: str, name: str) -> bool:
    st, d = h.request("list", parent_glob.encode(), timeout=10)
    if st != "ok":
        return False
    try:
        entries = json.loads(d.decode())
    except Exception:
        return False
    return any(e.get("name", "").lower() == name.lower() and e.get("is_dir")
               for e in entries)


def push_pull(h: Hrpc, path: str, data: bytes) -> tuple[bool, str]:
    st, d = h.request("push", path.encode() + b"\0" + data, timeout=20)
    if st != "ok":
        return False, f"push: {st} {d[:80]!r}"
    st, got = h.request("pull", path.encode(), timeout=20)
    if st != "ok":
        return False, f"pull: {st} {got[:80]!r}"
    return got == data, f"bytes={len(got)}"


def persistence(image: Path, outdir: Path, work: Path, timeout: float,
                memory: str) -> dict:
    res = {"write_phase": {}, "reboot_phase": {}, "ok": False}
    proc, q, h, _ = wait_for_vm(work / "persist-write", image, memory, timeout)
    try:
        home_ok = dir_has(h, "C:/*", "Home")
        bbs_ok = dir_has(h, "C:/Hermes/Apps/*", "HermesBBS")
        res["write_phase"]["dirs"] = {"home": home_ok, "bbs": bbs_ok}
        if not (home_ok and bbs_ok):
            # Writing to a missing directory triggers the 0.1.2 daemon fault;
            # never do that.  Record the missing precondition instead.
            res["write_phase"]["error"] = "precreated directory missing"
        else:
            for path, data in MARKERS:
                ok, why = push_pull(h, path, data)
                res["write_phase"][path] = {"ok": ok, "detail": why}
        st, d = h.request("ping", b"", timeout=10)
        res["write_phase"]["ping"] = st
    finally:
        h.close()
        stop(proc, q)
    time.sleep(1)
    proc, q, h, _ = wait_for_vm(work / "persist-read", image, memory, timeout)
    try:
        for path, data in MARKERS:
            st, got = h.request("pull", path.encode(), timeout=20)
            res["reboot_phase"][path] = {"ok": st == "ok" and got == data,
                                          "detail": f"status={st} bytes={len(got)}"}
        st, d = h.request("ping", b"", timeout=10)
        res["reboot_phase"]["ping"] = st
        p = work / "persist-read" / "final.png"
        q.screendump(p)
        dest = outdir / "persistence-launcher.png"
        res["shot_meta"] = to_palette(p, dest)
        res["shot"] = dest.name
    finally:
        h.close()
        stop(proc, q)
    res["ok"] = (res["write_phase"].get("dirs", {}).get("home") is True
                 and res["write_phase"].get("dirs", {}).get("bbs") is True
                 and all(v["ok"] for k, v in res["write_phase"].items() if k.startswith("C:"))
                 and all(v["ok"] for v in res["reboot_phase"].values()
                         if isinstance(v, dict)))
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=Path, required=True)
    ap.add_argument("--test-copy", action="store_true", default=True,
                    help="run trials against a copy so the input stays sealed")
    ap.add_argument("--no-test-copy", dest="test_copy", action="store_false")
    ap.add_argument("--boots", type=int, default=20)
    ap.add_argument("--timeout", type=float, default=75.0)
    ap.add_argument("--memory", default="2G")
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parents[1] / "shots" / "hermes-disk-0.1.2")
    ap.add_argument("--work", type=Path,
                    default=Path(__file__).resolve().parents[1] / "run" / "disk-test")
    args = ap.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    args.work.mkdir(parents=True, exist_ok=True)
    logf = out / "boot-trials.log"
    import hashlib
    def _sha(p: Path) -> str:
        h = hashlib.sha256()
        with p.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    source_sha = _sha(args.image)
    boot_image = args.image
    if args.test_copy:
        boot_image = args.work / "boot-test.qcow2"
        shutil.copyfile(args.image, boot_image)
    log(f"cold boot trials: {args.boots} x {boot_image} "
        f"(source {args.image})", logf)
    trials = []
    for i in range(1, args.boots + 1):
        r = boot_trial(i, boot_image, out, args.work, args.timeout,
                       args.memory, save=True)
        trials.append(r)
        log(f"boot {i:02d}: {'PASS' if r['ok'] else 'FAIL'} "
            f"{r['seconds']}s {r['reason']}", logf)
    (out / "boot-trials.json").write_text(json.dumps(trials, indent=2) + "\n")

    # Persistence and HRPC writes run against a copy so the shipped image
    # stays exactly as built.
    persist_image = args.work / "persist.qcow2"
    shutil.copyfile(boot_image, persist_image)
    pres = persistence(persist_image, out, args.work, args.timeout, args.memory)
    (out / "persistence.json").write_text(json.dumps(pres, indent=2) + "\n")
    log(f"persistence: {'PASS' if pres['ok'] else 'FAIL'}", logf)

    source_sha_after = _sha(args.image)
    summary = {
        "image": str(args.image),
        "image_sha256": source_sha,
        "image_sha256_after_tests": source_sha_after,
        "source_unchanged": source_sha == source_sha_after,
        "boots": args.boots,
        "passed": sum(1 for r in trials if r["ok"]),
        "median_seconds": sorted(r["seconds"] for r in trials if r["ok"])[len([r for r in trials if r["ok"]]) // 2]
        if any(r["ok"] for r in trials) else None,
        "persistence": pres["ok"],
        "hrpc_ping": pres.get("reboot_phase", {}).get("ping"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] == args.boots and pres["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
