#!/usr/bin/env python3
"""Boot TempleOfHermes-0.1.0.ISO and prove each guest feature over HRPC + screenshots."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hrpc import Hrpc  # noqa: E402
from qemu_hermes import (  # noqa: E402
    QMP,
    ROOT,
    RUN,
    SHOTS,
    glyph_text,
    start_vm,
    stop_vm,
)

ISO = ROOT / "dist" / "TempleOfHermes-0.1.0.ISO"
DISK = RUN / "hermes-smoke.qcow2"
SHOT = SHOTS
TRANSCRIPT = SHOTS / "serial-transcript.txt"
RESULTS = SHOTS / "smoke-results.json"


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S") + " " + msg, flush=True)


def shot(qmp: QMP, name: str) -> dict:
    dest = SHOT / f"{name}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    qmp.screendump(dest)
    rec = {"png": str(dest), "text": ""}
    try:
        rec["text"] = glyph_text(dest)
        (SHOT / f"{name}.txt").write_text(rec["text"])
        log(f"shot {name}: {rec['text'][:160]!r}")
    except Exception as e:
        rec["text"] = f"<ocr error: {e}>"
        log(f"shot {name}: ocr failed {e}")
    return rec


def main() -> int:
    if not ISO.is_file():
        log(f"missing ISO {ISO}")
        return 2
    SHOT.mkdir(parents=True, exist_ok=True)
    RUN.mkdir(parents=True, exist_ok=True)
    if DISK.exists():
        DISK.unlink()
    subprocess.check_call(["qemu-img", "create", "-f", "qcow2", str(DISK), "2G"])
    meta = start_vm("hermes-smoke", ISO, DISK, memory="2G", boot="d")
    log(f"qemu pid {meta['pid']}")
    time.sleep(1)
    qmp = QMP(Path(meta["qmp"]), timeout=60)
    cli = Hrpc(Path(meta["com1"]), timeout=60, log=RUN / "smoke-com1.log")
    results: dict = {"features": {}, "shots": {}}
    try:
        log("waiting for HBEACON")
        # First boot of a new kernel+Adam in TCG can take several minutes.
        beacon = cli.wait_beacon(timeout=900)
        log(f"beacon: {beacon}")
        results["beacon"] = beacon
        time.sleep(4)
        results["shots"]["boot_user"] = shot(qmp, "01-boot-user")

        st, payload = cli.request("ping", timeout=30)
        results["features"]["daemon_ping"] = {
            "status": st,
            "payload": payload.decode("utf-8", "replace"),
        }
        log(f"ping {st} {payload!r}")

        st, payload = cli.request("text", b"focus", timeout=30)
        results["features"]["exact_text_focus"] = {
            "status": st,
            "payload": payload.decode("utf-8", "replace")[:4000],
        }
        log(f"text {st} {payload[:200]!r}")

        st, payload = cli.request("tasks", timeout=30)
        results["features"]["tasks"] = {
            "status": st,
            "payload": payload.decode("utf-8", "replace")[:4000],
        }

        st, payload = cli.request("mode", b"agent", timeout=30)
        results["features"]["mode_agent"] = {
            "status": st,
            "payload": payload.decode("utf-8", "replace"),
        }
        time.sleep(1)
        results["shots"]["agent_banner"] = shot(qmp, "02-agent-banner")

        st, payload = cli.request("mouse", b"200,120", timeout=30)
        results["features"]["agent_cursor"] = {
            "status": st,
            "payload": payload.decode("utf-8", "replace"),
        }
        time.sleep(0.5)
        results["shots"]["agent_cursor"] = shot(qmp, "03-agent-cursor")

        src = b'"Hello from Hermes";\n"%d\\n",6*7;\n'
        st, payload = cli.request("eval", src, timeout=60)
        results["features"]["eval_holyc"] = {
            "status": st,
            "payload": payload.decode("utf-8", "replace"),
        }
        time.sleep(1)
        results["shots"]["eval_hello"] = shot(qmp, "04-eval-hello")
        st, payload = cli.request("text", b"focus", timeout=30)
        results["features"]["text_after_eval"] = {
            "status": st,
            "payload": payload.decode("utf-8", "replace")[:4000],
        }

        # Safe-mode: ask the agent to run OSInstall; the gate should refuse.
        st, payload = cli.request("eval", b"OSInstall(FALSE);\n", timeout=60)
        results["features"]["guard_osinstall"] = {
            "status": st,
            "payload": payload.decode("utf-8", "replace"),
        }
        st, payload = cli.request("events", timeout=30)
        results["features"]["events"] = {
            "status": st,
            "payload": payload.decode("utf-8", "replace")[:4000],
        }
        results["async_events"] = cli.events[-20:]
        time.sleep(0.5)
        results["shots"]["guard"] = shot(qmp, "05-guard-blocked")

        st, payload = cli.request("clip_set", b"clip from host", timeout=30)
        st, payload = cli.request("clip_get", timeout=30)
        results["features"]["clipboard"] = {
            "status": st,
            "payload": payload.decode("utf-8", "replace"),
        }

        st, payload = cli.request("list", b"/Adam/Hermes", timeout=30)
        results["features"]["files_list"] = {
            "status": st,
            "payload": payload.decode("utf-8", "replace"),
        }

        st, payload = cli.request("mode", b"user", timeout=30)
        results["features"]["mode_user"] = {
            "status": st,
            "payload": payload.decode("utf-8", "replace"),
        }
        time.sleep(1)
        results["shots"]["back_to_user"] = shot(qmp, "06-back-to-user")
        results["idle"] = cli.request("idle", timeout=30)[1].decode("utf-8", "replace")
    finally:
        TRANSCRIPT.write_text(cli.text())
        RESULTS.write_text(json.dumps(results, indent=2))
        log(f"transcript {TRANSCRIPT}")
        try:
            shot(qmp, "99-smoke-final")
        except Exception:
            pass
        cli.close()
        stop_vm(meta, qmp)
        qmp.close()
    # A couple of obvious pass/fail checks for the report.
    failures = []
    if "TempleOfHermes/0.1.0" not in results.get("beacon", ""):
        failures.append("missing HBEACON")
    ping = results.get("features", {}).get("daemon_ping", {})
    if ping.get("status") != "ok":
        failures.append("ping failed")
    text = results.get("features", {}).get("text_after_eval", {}).get("payload", "")
    if "Hello from Hermes" not in text and "42" not in text:
        # The eval output might be in eval_holyc instead of the focus dump.
        ev = results.get("features", {}).get("eval_holyc", {}).get("payload", "")
        if "Hello from Hermes" not in ev and "42" not in ev:
            failures.append("eval did not return Hello/42")
    evs = results.get("features", {}).get("events", {}).get("payload", "") + "\n".join(
        results.get("async_events") or []
    )
    if "danger_blocked" not in evs and "blocked" not in results.get("features", {}).get(
        "guard_osinstall", {}
    ).get("payload", ""):
        failures.append("guard did not fire")
    boot_txt = results.get("shots", {}).get("boot_user", {}).get("text", "")
    if "TEMPLE OF HERMES" not in boot_txt.upper() and "HERMES" not in boot_txt.upper():
        failures.append("boot screenshot missing HERMES branding (OCR may be weak)")
    results["failures"] = failures
    RESULTS.write_text(json.dumps(results, indent=2))
    log("failures: " + (repr(failures) if failures else "none"))
    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"SMOKE FAILED: {type(e).__name__}: {e}")
        raise
