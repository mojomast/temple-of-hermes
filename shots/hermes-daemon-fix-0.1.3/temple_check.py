#!/usr/bin/env python3
"""Temple entry check: click/key on the home entry must keep a clean launcher."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shots" / "hermes-daemon-fix-0.1.3"))

import capture  # noqa: E402

OUT = capture.OUT
RESULT = OUT / "temple-check.json"


def clean_home(vm: capture.VM) -> tuple[bool, str]:
    p, t = vm.shot("temple")
    if "Click an icon" not in t:
        return False, "launcher not visible"
    ok, why, _ = capture.overlap_ok(vm.meta)
    if not ok:
        return False, why
    return True, "clean launcher"


def run(method: str) -> dict:
    vm = capture.VM(f"temple-{method}")
    try:
        ok, why, _ = capture.wait_launcher(vm, 80)
        if not ok:
            return {"ok": False, "reason": "boot: " + why}
        home, _ = vm.shot("home-temple")
        if method == "click":
            x, y = capture.icon_xy(0)
            vm.q.mouse_click_at(x, y)
        else:
            vm.q.send_qcodes("t")
        time.sleep(3)
        for _ in range(20):
            ok2, why2 = clean_home(vm)
            if ok2:
                p, _ = vm.shot("temple-final")
                vm.save(p, f"app-temple-{method}.png", {})
                return {"ok": True, "reason": why2}
            time.sleep(2)
        return {"ok": False, "reason": why2}
    finally:
        vm.close()


def main() -> int:
    state = {}
    if RESULT.is_file():
        try:
            state = json.loads(RESULT.read_text())
        except Exception:
            state = {}
    for method in ("click", "key"):
        if state.get(method, {}).get("ok"):
            continue
        state[method] = run(method)
        RESULT.write_text(json.dumps(state, indent=2) + "\n")
    ok = all(state.get(m, {}).get("ok") for m in ("click", "key"))
    print(json.dumps(state, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
