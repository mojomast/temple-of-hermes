#!/usr/bin/env python3
"""Boot the integrated ISO and capture the TOH-INT evidence shots.

All waits are bounded.  Images are only processed with Python/PIL (size,
palette/index, non-black bbox); this script never opens an image for visual
inspection.
"""
from __future__ import annotations

import json
import subprocess
import threading
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "host"))

from qemu_hermes import QMP, ROOT as QROOT, RUN, glyph_text, start_vm, stop_vm  # noqa: E402
from hermes_daemon_client import HermesDaemonClient  # noqa: E402

ISO = ROOT / "dist" / "TempleOfHermes-0.1.0.ISO"
OUT = ROOT / "shots" / "hermes-integration"
TOOLS = ROOT / "shots" / "hermes-tools"
DISK = RUN / "hermes-shots.qcow2"
WAIT = 180.0
EGA = [
    (0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170),
    (170, 0, 0), (170, 0, 170), (170, 85, 0), (170, 170, 170),
    (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255),
    (255, 85, 85), (255, 85, 255), (255, 255, 85), (255, 255, 255),
]


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S") + " " + msg, flush=True)


def pil_check(png: Path) -> dict:
    im = Image.open(png)
    size = list(im.size)
    mode = im.mode
    if mode in ("P", "L"):
        indices = sorted({int(v) for v in im.getdata()})
        colors = []
        if mode == "P":
            pal = im.getpalette() or []
            colors = [tuple(pal[i * 3:i * 3 + 3]) for i in indices]
        else:
            colors = [(v, v, v) for v in indices]
        bad = [i for i in indices if i > 15]
        return {
            "path": str(png.relative_to(ROOT)),
            "size": size,
            "mode": mode,
            "indices": indices,
            "palette_0_15": not bad,
            "unique_colors": len(indices),
            "bbox": list(im.convert("L").getbbox() or (0, 0, 0, 0)),
        }
    rgb = im.convert("RGB")
    colors = sorted(set(rgb.getdata()))
    mapped = sorted({min(range(16), key=lambda i: sum((c[j] - EGA[i][j]) ** 2 for j in range(3))) for c in colors})
    exact = sum(1 for c in colors if c in EGA)
    bbox = list(rgb.convert("L").getbbox() or (0, 0, 0, 0))
    return {
        "path": str(png.relative_to(ROOT)),
        "size": size,
        "mode": mode,
        "indices": mapped,
        "palette_0_15": max(mapped) <= 15,
        "unique_colors": len(colors),
        "exact_ega_colors": exact,
        "bbox": bbox,
    }


class Drainer:
    """Continuously read COM1 so QEMU's serial buffer never backs up."""

    def __init__(self, cli: HermesDaemonClient) -> None:
        self.cli = cli
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.cli.drain(0.1)
            except Exception:
                return

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None


def shot(qmp: QMP, name: str, dest_dir: Path = OUT) -> dict:
    dest = dest_dir / f"{name}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    qmp.screendump(dest)
    rec = pil_check(dest)
    try:
        txt = glyph_text(dest)
        (dest_dir / f"{name}.txt").write_text(txt)
        rec["text"] = txt[:300]
    except Exception as e:
        rec["text"] = f"<ocr error: {type(e).__name__}>"
    log(f"shot {name} {rec['size']} colors={rec['unique_colors']} idx={rec['indices']} bbox={rec['bbox']}")
    return rec


def wait_text(qmp: QMP, needle: str, timeout: float = WAIT) -> str:
    deadline = time.time() + timeout
    last = ""
    n = 0
    while time.time() < deadline:
        n += 1
        tmp = OUT / "_wait.png"
        qmp.screendump(tmp)
        try:
            last = glyph_text(tmp)
        except Exception as e:
            last = f"<ocr error: {e}>"
        if needle.lower() in last.lower():
            tmp.unlink(missing_ok=True)
            return last
        time.sleep(3)
    tmp.unlink(missing_ok=True)
    return last


def run_app(cli: HermesDaemonClient, qmp: QMP, app: str, title: str, name: str, drainer: "Drainer" | None = None) -> dict:
    try:
        cli.call("task_kill", "Hermes Apps", timeout=20)
    except Exception:
        pass
    time.sleep(1)
    rec: dict = {}
    try:
        rec["eval"] = cli.eval(
            f'Spawn(&THLaunch,StrNew("::/Hermes/Apps/{app}/Run.HC"),"{title}");',
            timeout=30,
        )
    except Exception as e:
        rec["eval_error"] = f"{type(e).__name__}: {e}"
    if drainer is not None:
        drainer.start()
    time.sleep(10)
    if drainer is not None:
        drainer.stop()
    try:
        rec["focus"] = cli.window_focus(title, timeout=20)
    except Exception as e:
        rec["focus_error"] = f"{type(e).__name__}: {e}"
    time.sleep(2)
    rec.update(shot(qmp, name))
    rec["windows"] = cli.windows(timeout=20)
    try:
        cli.call("task_kill", title, timeout=20)
    except Exception:
        pass
    time.sleep(1)
    return rec


def main() -> int:
    if not ISO.is_file():
        log(f"missing ISO {ISO}")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    TOOLS.mkdir(parents=True, exist_ok=True)
    if DISK.exists():
        DISK.unlink()
    subprocess.check_call(["qemu-img", "create", "-f", "qcow2", str(DISK), "2G"])
    rundir = RUN / "hermes-shots"
    rundir.mkdir(parents=True, exist_ok=True)
    com2 = rundir / "com2.sock"
    if com2.exists():
        com2.unlink()
    extra = ["-serial", f"unix:{com2},server=on,wait=off"]
    meta = start_vm("hermes-shots", ISO, DISK, memory="2G", boot="d", extra=extra)
    log(f"qemu pid {meta['pid']}")
    time.sleep(1)
    qmp = QMP(Path(meta["qmp"]), timeout=60)
    cli = HermesDaemonClient(str(meta["com1"]), timeout=60)
    drainer = Drainer(cli)
    drainer.start()
    results: dict = {"shots": {}, "apps": {}, "tools": {}, "checks": []}
    relay = None
    try:
        # Early boot splash (bounded, no OCR dependency).
        time.sleep(6)
        results["shots"]["00-boot-splash"] = shot(qmp, "00-boot-splash")
        txt = wait_text(qmp, "Install onto hard drive", timeout=25)
        if "install onto hard drive" in txt.lower():
            qmp.type_text("n\n")
            time.sleep(2)
        wait_text(qmp, "TEMPLE OF HERMES", timeout=30)
        time.sleep(8)
        results["shots"]["01-home"] = shot(qmp, "01-home-launcher")

        drainer.stop()
        try:
            results["beacon"] = cli.beacons[-1] if cli.beacons else None
        except Exception:
            results["beacon"] = None
        for attempt in range(6):
            try:
                results["ping"] = cli.ping(timeout=30)
                break
            except Exception as e:
                results["ping_error"] = f"{type(e).__name__}: {e}"
                time.sleep(5)
        try:
            results["launcher_helper"] = cli.eval(
                'U0 THLaunch(U8 *p){ExeFile(p);Free(p);}\n', timeout=30
            )
        except Exception as e:
            results["launcher_helper_error"] = f"{type(e).__name__}: {e}"
        drainer.start()

        # COM2 relay for Hermes Chat (offline deterministic responder).
        relay = subprocess.Popen(
            [sys.executable, str(ROOT / "host" / "hermes_chat_relay.py"),
             "--enable", "--allow", "hermes", "--connect", str(com2)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(2)

        apps = [
            ("HermesChat", "Hermes Chat", "10-hermes-chat"),
            ("WorldSim", "WorldSim", "11-worldsim"),
            ("Codex", "Codex of Nous", "12-codex"),
            ("Psyche", "Psyche", "13-psyche"),
            ("Capybara", "Capybara Pet", "14-capybara"),
            ("MessengerRun", "Messenger Run", "15-messenger-run"),
            ("HermesBBS", "Hermes BBS", "16-hermes-bbs"),
            ("Threshold", "The Threshold", "17-threshold"),
            ("Dojo", "Hermes Dojo", "18-dojo"),
            ("Offerings", "Offerings", "19-offerings"),
        ]
        for app, title, name in apps:
            try:
                results["apps"][app] = run_app(cli, qmp, app, title, name, drainer)
            except Exception as e:
                results["apps"][app] = {"error": f"{type(e).__name__}: {e}"}
                try:
                    results["apps"][app]["shot"] = shot(qmp, name)
                except Exception:
                    pass

        drainer.stop()
        # B5 guest-tools RPC evidence.
        try:
            results["tools"]["toast"] = cli.toast("B5 toast: integration guest is live", timeout=20)
            time.sleep(1)
            results["shots"]["20-tools-toast"] = shot(qmp, "20-tools-toast", TOOLS)
        except Exception as e:
            results["tools"]["toast"] = {"error": f"{type(e).__name__}: {e}"}
        try:
            results["tools"]["windows"] = cli.windows(timeout=20)
            results["shots"]["21-tools-windows"] = shot(qmp, "21-tools-windows", TOOLS)
        except Exception as e:
            results["tools"]["windows"] = {"error": f"{type(e).__name__}: {e}"}
        try:
            results["tools"]["mode_agent"] = cli.mode("agent", timeout=20)
            results["tools"]["guards"] = cli.guards("Fmt", timeout=20)
            time.sleep(1)
            results["shots"]["22-tools-guards"] = shot(qmp, "22-tools-guards", TOOLS)
            cli.mode("user", timeout=20)
        except Exception as e:
            results["tools"]["guards"] = {"error": f"{type(e).__name__}: {e}"}
        try:
            results["tools"]["sysinfo"] = cli.sysinfo(timeout=20)
            results["shots"]["23-tools-sysinfo"] = shot(qmp, "23-tools-sysinfo", TOOLS)
        except Exception as e:
            results["tools"]["sysinfo"] = {"error": f"{type(e).__name__}: {e}"}
        try:
            results["tools"]["events"] = cli.take_events()[-10:]
        except Exception:
            pass
    finally:
        try:
            drainer.stop()
        except Exception:
            pass
        if cli is not None:
            try:
                cli.close()
            except Exception:
                pass
        if relay is not None:
            relay.terminate()
            try:
                relay.wait(timeout=5)
            except Exception:
                relay.kill()
        try:
            stop_vm(meta, qmp)
        except Exception:
            pass
        qmp.close()
    (OUT / "shots.json").write_text(json.dumps(results, indent=2))
    (TOOLS / "tools.json").write_text(json.dumps(results.get("tools", {}), indent=2))
    ok = all(v.get("palette_0_15", False) for v in results["shots"].values() if isinstance(v, dict))
    results["checks"].append({"name": "all_png_palette_0_15", "passed": ok})
    (OUT / "shots.json").write_text(json.dumps(results, indent=2))
    log("palette check: " + str(ok))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
