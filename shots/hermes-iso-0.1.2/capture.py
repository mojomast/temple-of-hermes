#!/usr/bin/env python3
"""Live-CD checks for TempleOfHermes-0.1.2.  PIL/OCR only; never shows images."""
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

from hrpc import Hrpc  # noqa: E402
from qemu_hermes import QMP, SHOTS, glyph_text, start_vm, stop_vm  # noqa: E402

ISO = ROOT / "dist" / "TempleOfHermes-0.1.2.ISO"
OUT = ROOT / "shots" / "hermes-iso-0.1.2"
RAW = SHOTS / "_raw" / "iso-0.1.2"
STATE = OUT / "capture-state.json"

PALETTE = [
    (0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170),
    (170, 0, 0), (170, 0, 170), (170, 85, 0), (170, 170, 170),
    (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255),
    (255, 85, 85), (255, 85, 255), (255, 255, 85), (255, 255, 255),
]

COLS, GRID_TOP, GRID_BOTTOM = 6, 44, 26
BAD_PHRASES = (
    "Take Tour", "Install onto hard drive", "System Keys Quick Guide",
    "AutoComplete is in StandBy", "Works Everywhere", "Install onto",
)

# name, registry index, shortcut, expected on-screen tokens
APPS = [
    ("hermes-chat", 1, "h", ["COM2 modem, destination", "you>"]),
    ("worldsim", 2, "w", ["EVENT LOG", "WORLDSIM"]),
    ("codex", 3, "c", ["A browser for the lore", "CODEX OF NOUS"]),
    ("psyche", 4, "p", ["SIGNAL FIELD", "VISUALIZATION ONLY"]),
    ("capybara", 5, "b", ["temple pet", "CAPYBARA"]),
    ("messenger", 6, "m", ["DELIVERED", "HUMAN PLAY", "AUTOPILOT"]),
    ("bbs", 7, "s", ["HERMES BBS", "HBBS/1"]),
    ("threshold", 8, "r", ["fictional host from the Nous universe", "Threshold"]),
    ("dojo", 9, "j", ["HERMES DOJO", "TEKNIUM"]),
    ("offerings", 10, "o", ["DON PIEDRO'S OFFERINGS", "Spoons only"]),
    ("southpaw", 11, "u", ["BBS highlights, announced", "Southpaw is a face"]),
    ("modem-net", 12, "n", ["HERMES/NET modem status", "Modem / Net"]),
    ("caduceus", 13, "d", ["CADUCEUS - TEMPLE SERPENT", "Guide the temple serpent"]),
    ("token-rain", 14, "k", ["ARETE CATCH", "NOUS GIRL AT THE THRESHOLD"]),
    ("spoon", 15, "q", ["SPOON RALLY", "Catch Don Piedro"]),
    ("dojo-duel", 16, "l", ["a timed HolyC typing duel", "Type the HolyC token"]),
    ("about", 17, "a", ["About THE TEMPLE OF HERMES", "What this is"]),
]


def log(msg: str) -> None:
    line = (time.strftime("%H:%M:%S ") + msg).rstrip()
    print(line, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
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
    cache: dict[tuple[int, int, int], int] = {}
    out = Image.new("P", im.size)
    ip, op = im.load(), out.load()
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
                cache[rgb] = i
            op[x, y] = i
    out.putpalette([c for rgb in PALETTE for c in rgb] + [0] * (768 - 48))
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    return {"size": [640, 480], "mode": out.mode,
            "colors": len(set(out.getdata()))}


def bad_text(text: str) -> list[str]:
    return [p for p in BAD_PHRASES if p.lower() in text.lower()]


def windows(meta: dict, timeout: float = 8.0) -> list[dict] | None:
    for _ in range(3):
        h = None
        try:
            h = Hrpc(Path(meta["com1"]), timeout=timeout)
            st, data = h.request("windows", b"", timeout=timeout)
            if st == "ok":
                return json.loads(data.decode("utf-8", "replace")).get("windows", [])
        except Exception:
            pass
        finally:
            if h:
                h.close()
        time.sleep(1.0)
    return None


def overlap_ok(meta: dict) -> tuple[bool, str, list]:
    ws = windows(meta)
    if ws is None:
        return False, "HRPC windows unavailable", []
    launchers = [w for w in ws if w.get("title") == "Hermes Apps"]
    others = [w for w in ws if w.get("title") != "Hermes Apps"]
    if len(launchers) != 1:
        return False, f"launcher windows={len(launchers)}", ws
    if others:
        return False, "other visible windows: " + ", ".join(
            f"{w.get('title')}@{w.get('win')}" for w in others), ws
    return True, "only the launcher is visible", ws


class VM:
    def __init__(self, name: str, serial2: bool = False):
        self.meta = start_vm(name, ISO, None, memory="2G", boot="d", serial2=serial2)
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

    def save(self, src: Path, name: str, state: dict) -> dict:
        info = to_palette(src, OUT / name)
        state[name] = {"ok": True, **info}
        save_state(state)
        return info

    def close(self) -> None:
        try:
            stop_vm(self.meta, self.q)
        except Exception:
            pass
        try:
            self.q.close()
        except Exception:
            pass


def wait_launcher(vm: VM, timeout: float = 75.0) -> tuple[bool, str, list]:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        p, t = vm.shot("launcher")
        last = t
        if "Click an icon" in t or ("Hermes Apps" in t and "THE TEMPLE OF HERMES" in t):
            bad = bad_text(t)
            if bad:
                last = "overlap text: " + ", ".join(bad)
            else:
                okw, why, ws = overlap_ok(vm.meta)
                if okw:
                    return True, "ok", ws
                last = why
        time.sleep(2)
    return False, "launcher not clean: " + last[-200:], []


def close_launcher(vm: VM) -> bool:
    for _ in range(4):
        p, t = vm.shot("pre-esc")
        if "Click an icon" not in t:
            return True
        vm.q.send_qcodes("shift", "esc")
        time.sleep(2)
    p, t = vm.shot("post-esc")
    return "Click an icon" not in t


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
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    pa, pb = ia.load(), ib.load()
    n = 0
    for y in range(0, 480, 4):
        for x in range(0, 640, 4):
            if pa[x, y] != pb[x, y]:
                n += 1
    return n / float((480 // 4) * (640 // 4))


def icon_xy(idx: int) -> tuple[int, int]:
    row, col = divmod(idx, COLS)
    x = 8 + col * 104 + 52
    y = 8 + 48 + row * 128 + 8 + 16
    return x, y


def color_count(p: Path) -> int:
    im = Image.open(p).convert("RGB")
    px = im.load()
    seen = set()
    for y in range(0, 480, 8):
        for x in range(0, 640, 8):
            seen.add(px[x, y])
            if len(seen) > 8:
                return len(seen)
    return len(seen)


def wait_app(vm: VM, tokens: list[str], home: Path,
             timeout: float = 40.0) -> tuple[bool, str, Path]:
    deadline = time.time() + timeout
    p = vm.raw / "none.png"
    last = ""
    while time.time() < deadline:
        p, t = vm.shot("app")
        last = t
        ws = windows(vm.meta)
        others = [w for w in ws if w.get("title") != "Hermes Apps"] if ws else []
        diff = px_diff(home, p)
        colors = color_count(p)
        hit = any(k.lower() in t.lower() for k in tokens)
        if hit and diff > 0.10:
            return True, f"app text, diff={diff:.2f}, colors={colors}", p
        if others and colors >= 5 and diff > 0.18 and "Click an icon" not in t:
            return True, f"app window {others[0].get('title','')}, diff={diff:.2f}, colors={colors}", p
        time.sleep(2)
    return False, "no app UI; last=" + last[-160:], p


def wait_return(vm: VM, timeout: float = 45.0) -> tuple[bool, str, Path]:
    deadline = time.time() + timeout
    p = vm.raw / "none.png"
    last = ""
    while time.time() < deadline:
        p, t = vm.shot("return")
        last = t
        if "Click an icon" in t and not bad_text(t):
            okw, why, ws = overlap_ok(vm.meta)
            if okw or not ws:
                return True, "launcher back", p
            last = why
        time.sleep(2)
    return False, "no launcher return; last=" + last[-160:], p


def exit_app(vm: VM) -> None:
    vm.q.send_qcodes("shift", "esc")
    time.sleep(1.5)
    vm.q.send_qcodes("esc")
    time.sleep(1.5)
    vm.q.send_qcodes("esc")
    time.sleep(1.0)


def capture_splash(state: dict) -> None:
    dest = OUT / "01-boot-splash.png"
    if dest.is_file():
        return
    vm = VM("splash")
    chosen = None
    p = None
    try:
        deadline = time.time() + 14
        while time.time() < deadline:
            p, t = vm.shot("boot")
            if "TinkerOS V5.200" in t and "FPS:" not in t:
                chosen = p
            if "FPS:" in t:
                break
            time.sleep(0.4)
        if chosen is None:
            chosen = p
        vm.save(chosen, dest.name, state)
        log(f"splash captured from {chosen.name if chosen else 'none'}")
    finally:
        vm.close()


def capture_home(state: dict) -> None:
    dest = OUT / "02-home-launcher.png"
    for attempt in range(1, 4):
        vm = VM(f"home-{attempt}")
        try:
            ok, why, ws = wait_launcher(vm, 80)
            if ok:
                p, t = vm.shot("home-final")
                vm.save(p, dest.name, state)
                log("home launcher captured: " + why)
                return
            log(f"home attempt {attempt}: {why}")
        finally:
            vm.close()
    log("home launcher FAILED")


def test_one(state: dict, name: str, idx: int, key: str, tokens: list[str],
             method: str) -> dict:
    vm = VM(f"app-{name}-{method}")
    try:
        ok, why, ws = wait_launcher(vm, 85)
        if not ok:
            log(f"{name} {method}: boot failed ({why})")
            return {"ok": False, "launch": "boot: " + why, "return": "", "diff": 0.0}
        home, _ = vm.shot("home")
        if method == "click":
            x, y = icon_xy(idx)
            vm.q.mouse_click_at(x, y)
        else:
            vm.q.send_qcodes(key)
        ok, why, p = wait_app(vm, tokens, home)
        diff = px_diff(home, p) if p.is_file() else 0.0
        vm.save(p, f"app-{name}-{method}{'' if ok else '-FAIL'}.png", state)
        log(f"{name} {method}: {'PASS' if ok else 'FAIL'} ({why}, diff={diff:.2f})")
        if ok:
            exit_app(vm)
            rok, rwhy, rp = wait_return(vm)
        else:
            rok, rwhy, rp = False, "launch failed", p
        if p.is_file() and rok is not None:
            vm.save(rp, f"return-{name}-{method}{'' if rok else '-FAIL'}.png", state)
        log(f"{name} {method} return: {'PASS' if rok else 'FAIL'} ({rwhy})")
        return {"ok": bool(ok and rok), "launch": why, "return": rwhy,
                "diff": round(diff, 3)}
    finally:
        vm.close()


def run_app_suite(state: dict) -> None:
    results = state.setdefault("apps", {})
    for name, idx, key, tokens in APPS:
        res = results.setdefault(name, {})
        for method in ("click", "key"):
            res[method] = test_one(state, name, idx, key, tokens, method)
            save_state(state)
    passed = sum(1 for r in results.values()
                 if r.get("click", {}).get("ok") and r.get("key", {}).get("ok"))
    log(f"app suite: {passed}/{len(APPS)} apps passed both click and key")

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
    for attempt in range(1, 4):
        vm = VM(f"net-{attempt}", serial2=True)
        stub = None
        try:
            if not wait_launcher(vm, 80)[0]:
                continue
            stub = Stub(vm.meta["com2"], OUT / "net-echo.log")
            stub.start()
            time.sleep(0.5)
            home, _ = vm.shot("home-net")
            vm.q.send_qcodes("n")
            ok, why, p = wait_app(vm, ["HERMES/NET", "Modem / Net"], home)
            if not ok:
                log(f"net: app launch failed: {why}")
                continue
            vm.q.send_qcodes("e")
            found = False
            for i in range(16):
                time.sleep(3)
                p, t = vm.shot(f"net-echo-{i}")
                if "ECHO OK" in t:
                    found = True
                    break
            vm.save(p, dest.name, state)
            log(f"net echo ok={found}")
            if found:
                exit_app(vm)
                wait_return(vm)
                return
        finally:
            if stub:
                stub.stop_flag = True
                stub.join(timeout=2)
            vm.close()
    log("net echo: FAILED")


def capture_shell(state: dict) -> None:
    dest = OUT / "20-shell.png"
    vm = VM("shell")
    try:
        if not wait_launcher(vm, 80)[0]:
            log("shell: no launcher")
            return
        try:
            h = Hrpc(Path(vm.meta["com1"]), timeout=10)
            st, d = h.request("eval", b'User("Cd(\\"T:/\\");\\n");\n', timeout=10)
            h.close()
            log(f"shell: User() {st}")
        except Exception as e:
            log(f"shell: User() failed: {e}")
        time.sleep(4)
        ok = False
        for a in range(8):
            vm.q.type_text("7*7;\n", delay=0.14)
            time.sleep(2.5)
            p, t = vm.shot(f"shell-marker-{a}")
            if "ans=0x00000031=49" in t:
                ok = True
                break
        if ok:
            vm.q.type_text('Cd("T:/Hermes/Apps/");\n', delay=0.14)
            time.sleep(1)
            vm.q.type_text('Dir("T:/Hermes/Apps");\n', delay=0.14)
            time.sleep(2)
            p, t = vm.shot("shell-final")
            vm.save(p, dest.name, state)
            log("shell captured")
        else:
            log("shell: marker not found")
    finally:
        vm.close()


def boot_trial(index: int, timeout: float = 75.0) -> dict:
    started = time.time()
    vm = VM(f"boot-{index:02d}")
    try:
        ok, why, ws = wait_launcher(vm, timeout)
        elapsed = round(time.time() - started, 1)
        return {"trial": index, "ok": ok, "seconds": elapsed,
                "reason": "" if ok else why, "windows": ws}
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
        capture_home(state)
    if only in ("", "apps"):
        run_app_suite(state)
    if only in ("", "net"):
        capture_net(state)
    if only in ("", "shell"):
        capture_shell(state)
    log("capture pass complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
