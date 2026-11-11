#!/usr/bin/env python3
"""Boot dist/TempleOfHermes-0.1.1.ISO under QEMU TCG and capture PIL-only shots.

Every wait is bounded.  One VM per target keeps a stuck guest from blocking the
others.  Screenshots are converted to a 16-colour CGA palette (indices 0-15).
"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from PIL import Image  # noqa: E402

from qemu_hermes import QMP, RUN, SHOTS, glyph_text, start_vm, stop_vm  # noqa: E402

ISO = ROOT / "dist" / "TempleOfHermes-0.1.1.ISO"
OUT = ROOT / "shots" / "hermes-iso-0.1.1"
RAW = SHOTS / "_raw" / "iso-0.1.1"
STATE = OUT / "capture-state.json"

PALETTE = [
    (0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170),
    (170, 0, 0), (170, 0, 170), (170, 85, 0), (170, 170, 170),
    (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255),
    (255, 85, 85), (255, 85, 255), (255, 255, 85), (255, 255, 255),
]

APPS = [
    ("03-app-hermes-chat", "Hermes Chat", "T:/Hermes/Apps/HermesChat/Run.HC",
     ["Hermes Chat", "you>"], False),
    ("04-app-worldsim", "WorldSim", "T:/Hermes/Apps/WorldSim/Run.HC",
     ["WorldSim", "WORLD"], True),
    ("05-app-codex", "Codex", "T:/Hermes/Apps/Codex/Run.HC",
     ["Codex", "CODEX"], True),
    ("06-app-psyche", "Psyche", "T:/Hermes/Apps/Psyche/Run.HC",
     ["Psyche", "PSYCHE"], True),
    ("07-app-capybara", "Capybara", "T:/Hermes/Apps/Capybara/Run.HC",
     ["Capybara", "CAPYBARA"], True),
    ("08-app-messenger", "Messenger", "T:/Hermes/Apps/MessengerRun/Run.HC",
     ["Messenger", "MESSENGER"], True),
    ("09-app-bbs", "BBS", "T:/Hermes/Apps/HermesBBS/Run.HC",
     ["HERMES BBS", "OFFLINE", "BOARDS"], True),
    ("10-app-threshold", "Threshold", "T:/Hermes/Apps/Threshold/Run.HC",
     ["Threshold", "THRESHOLD"], True),
    ("11-app-dojo", "Dojo", "T:/Hermes/Apps/Dojo/Run.HC",
     ["Dojo", "DOJO"], True),
    ("12-app-offerings", "Offerings", "T:/Hermes/Apps/Offerings/Run.HC",
     ["Offerings", "OFFERINGS"], True),
    ("13-app-southpaw", "Southpaw", "T:/Hermes/Apps/Southpaw/Run.HC",
     ["Southpaw", "SOUTHPAW"], True),
    ("14-app-modem-net", "Modem / Net", "T:/Hermes/Apps/Net/Run.HC",
     ["HERMES/NET", "Modem / Net"], False),
    ("15-game-caduceus", "Caduceus", "T:/Hermes/Apps/Caduceus/Run.HC",
     ["Caduceus", "CADUCEUS", "SCORE"], True),
    ("16-game-token-rain", "Token Rain", "T:/Hermes/Apps/TokenRain/Run.HC",
     ["Token Rain", "TOKEN RAIN", "SCORE"], True),
    ("17-game-spoon", "Spoon", "T:/Hermes/Apps/Spoon/Run.HC",
     ["Spoon", "SPOON", "CATCH"], True),
    ("18-game-dojo-duel", "Dojo Duel", "T:/Hermes/Apps/DojoDuel/Run.HC",
     ["Dojo Duel", "DOJO DUEL", "DUEL"], True),
]


def log(msg: str) -> None:
    line = (time.strftime("%H:%M:%S ") + msg).rstrip()
    print(line, flush=True)
    (OUT / "capture.log").parent.mkdir(parents=True, exist_ok=True)
    with (OUT / "capture.log").open("a") as f:
        f.write(line + "\n")


def load_state() -> dict:
    if STATE.is_file():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, indent=2) + "\n")


def to_palette(src: Path, dest: Path) -> dict:
    im = Image.open(src).convert("RGB")
    if im.size != (640, 480):
        raise ValueError(f"{src} is {im.size}, not 640x480")
    pal = PALETTE
    cache: dict[tuple[int, int, int], int] = {}
    out = Image.new("P", im.size)
    ip = im.load()
    op = out.load()
    for y in range(480):
        for x in range(640):
            rgb = ip[x, y]
            i = cache.get(rgb)
            if i is None:
                if rgb in pal:
                    i = pal.index(rgb)
                else:
                    best = 0
                    bd = 1 << 30
                    for k, c in enumerate(pal):
                        d = (rgb[0] - c[0]) ** 2 + (rgb[1] - c[1]) ** 2 + (rgb[2] - c[2]) ** 2
                        if d < bd:
                            bd = d
                            best = k
                    i = best
                cache[rgb] = i
            op[x, y] = i
    flat = [c for rgb in pal for c in rgb] + [0] * (768 - 48)
    out.putpalette(flat)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    return {"file": dest.name, "size": [640, 480], "mode": out.mode,
            "colors": len(set(out.getdata())), "off_palette": 0}


class VM:
    def __init__(self, name: str):
        self.meta = start_vm(name, ISO, None, memory="2G", boot="d", serial2=True)
        time.sleep(1)
        self.q = QMP(Path(self.meta["qmp"]), timeout=60)
        self.raw = RAW / name
        self.raw.mkdir(parents=True, exist_ok=True)
        self.n = 0

    def shot(self, tag: str) -> tuple[Path, str]:
        self.n += 1
        p = self.raw / f"{self.n:03d}-{tag}.png"
        self.q.screendump(p)
        try:
            return p, glyph_text(p)
        except Exception:
            return p, ""

    def close(self) -> None:
        try:
            self.q.close()
        except Exception:
            pass
        try:
            stop_vm(self.meta, self.q)
        except Exception:
            pass


def wait_launcher(vm: VM, timeout: float = 75.0) -> bool:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        p, t = vm.shot("launcher")
        last = t
        if "Art icons" in t or "Click an icon" in t:
            return True
        time.sleep(3)
    return False


def close_launcher(vm: VM) -> bool:
    for _ in range(3):
        p, t = vm.shot("pre-esc")
        if "Art icons" not in t and "Click an icon" not in t:
            return True
        vm.q.send_qcodes("esc")
        time.sleep(2)
    p, t = vm.shot("post-esc")
    return "Art icons" not in t and "Click an icon" not in t


def focus_shell(vm: VM, tag: str = "shell") -> bool:
    for a in range(6):
        if a:
            vm.q.send_qcodes("ctrl", "alt", "n")
            time.sleep(1.2)
        vm.q.type_text("7*7;\n", delay=0.12)
        time.sleep(2.2)
        p, t = vm.shot(f"marker-{tag}-{a}")
        if "ans=0x00000031=49" in t:
            return True
    return False


def px_diff(a: Path, b: Path) -> float:
    ia = Image.open(a).convert("RGB")
    ib = Image.open(b).convert("RGB")
    pa, pb = ia.load(), ib.load()
    n = 0
    for y in range(0, 480, 4):
        for x in range(0, 640, 4):
            if pa[x, y] != pb[x, y]:
                n += 1
    return n / float((480 // 4) * (640 // 4))


def boot_to_shell(name: str) -> VM | None:
    vm = VM(name)
    if not wait_launcher(vm):
        log(f"{name}: launcher did not appear; rebooting")
        vm.close()
        return None
    if not close_launcher(vm):
        log(f"{name}: launcher did not close")
        vm.close()
        return None
    if not focus_shell(vm):
        log(f"{name}: shell focus failed")
        vm.close()
        return None
    return vm


def capture_target(entry, state: dict) -> None:
    name, title, run_path, keys, graphical = entry
    dest = OUT / f"{name}.png"
    if dest.is_file() and state.get(name, {}).get("ok"):
        log(f"{name}: already captured")
        return
    for attempt in range(1, 4):
        vm = boot_to_shell(f"cap-{name}-{attempt}")
        if vm is None:
            continue
        try:
            vm.q.type_text('Cd("T:/");\n', delay=0.14)
            time.sleep(1.0)
            _, pre_t = vm.shot("pre-launch")
            pre_path = vm.raw / f"{vm.n:03d}-pre-launch.png"
            vm.q.type_text(f'ExeFile("{run_path}");\n', delay=0.14)
            # The HolyC line editor occasionally drops the final Enter; send it
            # again after the text has settled so the command actually runs.
            time.sleep(2.5)
            vm.q.send_qcodes("ret")
            time.sleep(0.4)
            vm.q.send_qcodes("ret")
            best = None
            launch_ok = False
            errors = []
            for i in range(12):
                time.sleep(3.5)
                p, t = vm.shot(f"launch-{i}")
                hit = any(k.lower() in t.lower() for k in keys)
                diff = px_diff(pre_path, p)
                err = ("ERROR:" in t or "Error at" in t or
                       "Undefined identifier" in t or "Except:" in t)
                if err:
                    errors = [l.strip() for l in t.splitlines()
                              if "ERROR" in l or "Error at" in l or
                              "Undefined" in l or "Except:" in l][:4]
                # Command-line apps print into the shell, so their output is a
                # success even while the typed ExeFile line is still visible.
                hit_ok = hit and (not graphical or "ExeFile(" not in t)
                if diff > 0.15 or hit_ok or err:
                    launch_ok = True
                if err or hit_ok or diff > 0.3:
                    best = p
                    break
                if launch_ok and i >= 2:
                    best = p
                    break
            if best is None:
                best = p if 'p' in locals() else pre_path
                launch_ok = px_diff(pre_path, best) > 0.15
            info = to_palette(best, dest)
            state[name] = {"ok": bool(launch_ok), "title": title, "run": run_path,
                           "attempt": attempt, "errors": errors, **info}
            save_state(state)
            log(f"{name}: ok={launch_ok} diff={px_diff(pre_path, best):.2f} errors={errors}")
            if launch_ok:
                return
        finally:
            vm.close()
    log(f"{name}: FAILED after retries")


def capture_launcher_and_shell(state: dict) -> None:
    if not (OUT / "02-home-launcher.png").is_file():
        for attempt in range(1, 4):
            vm = VM(f"launcher-{attempt}")
            try:
                if wait_launcher(vm, 80):
                    p, t = vm.shot("launcher-final")
                    if "Art icons" in t or "Click an icon" in t:
                        info = to_palette(p, OUT / "02-home-launcher.png")
                        state["02-home-launcher"] = {"ok": True, "attempt": attempt, **info}
                        save_state(state)
                        log("launcher captured")
                        if close_launcher(vm) or True:
                            if focus_shell(vm, "shellshot"):
                                vm.q.type_text('Cd("T:/Hermes/Apps/");\n', delay=0.14)
                                time.sleep(1)
                                vm.q.type_text('Dir("T:/Hermes/Apps");\n', delay=0.14)
                                time.sleep(2)
                                p2, t2 = vm.shot("shell-final")
                                info2 = to_palette(p2, OUT / "20-shell.png")
                                state["20-shell"] = {"ok": True, **info2}
                                save_state(state)
                                log("shell captured")
                        return
            finally:
                vm.close()
        log("launcher: FAILED after retries")


def capture_splash(state: dict) -> None:
    dest = OUT / "01-boot-splash.png"
    if dest.is_file():
        return
    vm = VM("splash")
    chosen = None
    try:
        deadline = time.time() + 12
        while time.time() < deadline:
            p, t = vm.shot("boot")
            if "TinkerOS V5.200" in t and "FPS:" not in t:
                chosen = p
            if "FPS:" in t:
                break
            time.sleep(0.4)
        if chosen is None:
            chosen = p
        info = to_palette(chosen, dest)
        state["01-boot-splash"] = {"ok": True, **info}
        save_state(state)
        log(f"splash captured from {chosen.name}")
    finally:
        vm.close()


class Stub(threading.Thread):
    def __init__(self, path: str, log_path: Path):
        super().__init__(daemon=True)
        self.path = path
        self.log_path = log_path
        self.stop_flag = False
        self.payload = b""
        self.logf = log_path.open("wb")

    def run(self) -> None:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        for _ in range(100):
            try:
                s.connect(self.path)
                break
            except OSError:
                time.sleep(0.2)
        else:
            self.logf.write(b"# stub could not connect\n")
            self.logf.close()
            return
        s.settimeout(0.5)
        buf = b""
        while not self.stop_flag:
            try:
                d = s.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not d:
                break
            self.logf.write(b"guest->stub " + d.replace(b"\r", b"\\r").replace(b"\n", b"\\n") + b"\n")
            buf += d
            while b"\r" in buf:
                line, buf = buf.split(b"\r", 1)
                cmd = line.decode("latin-1")
                if cmd.startswith("ATZ"):
                    r = b"OK\r\n"
                elif cmd.startswith("ATD"):
                    r = b"CONNECT 115200\r\n"
                elif cmd.startswith("AT+SEND"):
                    try:
                        n = int(cmd.split()[1])
                    except Exception:
                        n = 0
                    while len(buf) < n:
                        try:
                            buf += s.recv(4096)
                        except socket.timeout:
                            break
                    self.payload, buf = buf[:n], buf[n:]
                    self.logf.write(b"stub payload " + self.payload + b"\n")
                    r = b"OK\r\n"
                elif cmd.startswith("AT+RECV"):
                    r = b"DATA %d\r\n" % len(self.payload) + self.payload
                elif cmd.startswith("ATH"):
                    r = b"OK\r\n"
                else:
                    r = b"ERROR\r\n"
                self.logf.write(b"stub->guest " + r.replace(b"\r", b"\\r").replace(b"\n", b"\\n") + b"\n")
                s.sendall(r)
        s.close()
        self.logf.close()


def capture_net(state: dict) -> None:
    dest = OUT / "19-net-echo.png"
    if dest.is_file():
        return
    for attempt in range(1, 4):
        vm = VM(f"net-{attempt}")
        stub = None
        try:
            if not wait_launcher(vm):
                continue
            if not close_launcher(vm):
                continue
            if not focus_shell(vm, "net"):
                continue
            stub = Stub(vm.meta["com2"], OUT / "net-echo.log")
            stub.start()
            time.sleep(0.5)
            vm.q.type_text('Cd("T:/");\n', delay=0.14)
            time.sleep(0.8)
            vm.q.type_text('ExeFile("T:/Hermes/Apps/Net/Run.HC");\n', delay=0.14)
            time.sleep(2.5)
            vm.q.send_qcodes("ret")
            time.sleep(6)
            vm.q.type_text('HermesNetEchoTest;\n', delay=0.14)
            time.sleep(2.5)
            vm.q.send_qcodes("ret")
            ok = False
            p = None
            for i in range(20):
                time.sleep(4)
                p, t = vm.shot(f"net-{i}")
                if "ECHO OK" in t:
                    ok = True
                    break
            if p is None:
                continue
            info = to_palette(p, dest)
            state["19-net-echo"] = {"ok": ok, "attempt": attempt, **info}
            save_state(state)
            log(f"net echo ok={ok}")
            if ok:
                return
        finally:
            if stub:
                stub.stop_flag = True
                stub.join(timeout=2)
            vm.close()
    log("net echo: FAILED")


def boot_trial(index: int, timeout: float = 75.0) -> dict:
    """One independent live-CD boot; launcher only, no writable disk."""
    started = time.time()
    name = f"boot-{index:02d}"
    vm = VM(name)
    try:
        ok = wait_launcher(vm, timeout)
        elapsed = round(time.time() - started, 1)
        reason = "" if ok else "launcher timeout (clock freeze or no draw)"
        return {"trial": index, "ok": ok, "seconds": elapsed, "reason": reason}
    finally:
        vm.close()


def capture_boot_trials(count: int = 20) -> None:
    dest = OUT / "boot-trials.json"
    logpath = OUT / "boot-trials.log"
    trials = []
    if dest.is_file():
        try:
            trials = json.loads(dest.read_text()).get("trials", [])
        except Exception:
            trials = []
    done = {t["trial"] for t in trials}
    for i in range(1, count + 1):
        if i in done:
            continue
        t = boot_trial(i)
        trials.append(t)
        dest.write_text(json.dumps({"trials": trials}, indent=2) + "\n")
        with logpath.open("a") as f:
            f.write(f"trial {i:02d} ok={t['ok']} seconds={t['seconds']} {t['reason']}".rstrip() + "\n")
        log(f"boot trial {i:02d}: ok={t['ok']} {t['seconds']}s {t['reason']}")
    passed = sum(1 for t in trials if t["ok"])
    log(f"boot trials: {passed}/{len(trials)}")


def main() -> int:
    if not ISO.is_file():
        print(f"missing {ISO}")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    state = load_state()
    only = os.environ.get("TOH_ONLY", "").strip()
    if only in ("", "bootrate"):
        capture_boot_trials(20)
    if only in ("", "splash"):
        capture_splash(state)
    if only in ("", "launcher"):
        capture_launcher_and_shell(state)
    if only in ("", "apps"):
        for entry in APPS:
            capture_target(entry, state)
    if only in ("", "net"):
        capture_net(state)
    log("capture pass complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
