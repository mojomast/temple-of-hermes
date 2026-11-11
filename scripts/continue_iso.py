#!/usr/bin/env python3
"""Wait for the stuck R3 receiver to time out, then AfterOverlay + MakeDistro + extract ISO."""
from __future__ import annotations

import hashlib
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_iso import DIST, ISO_NAME, LOG, SHOT, log, shot  # noqa: E402
from fat32_read import extract, open_first_fat  # noqa: E402
from qemu_hermes import QMP, RUN, glyph_text, stop_vm  # noqa: E402

QMP_PATH = RUN / "hermes-build" / "qmp.sock"
DISK = RUN / "hermes-build.qcow2"
PROMPT_DEADLINE = time.mktime(time.strptime("2026-11-09 16:35:00", "%Y-%m-%d %H:%M:%S"))
PAGE_AFTER = time.mktime(time.strptime("2026-11-09 16:22:00", "%Y-%m-%d %H:%M:%S"))


def tail_lines(text: str, n: int = 8) -> list[str]:
    return [ln.rstrip() for ln in text.splitlines() if ln.strip() and "EOF" not in ln][-n:]


def at_prompt(text: str) -> bool:
    lines = tail_lines(text, 12)
    if not lines:
        return False
    last = lines[-1].strip()
    # A real prompt, not "C:/>R3;" still running and not a "More" footer
    if last in ("C:/>", "C:/"):
        return True
    # Visible prompt near the end after an exception, even if More was on screen earlier
    for ln in reversed(lines):
        s = ln.strip()
        if s in ("C:/>", "C:/"):
            return True
        if s.endswith("R3;") or s.endswith("R2;") or "More" in s:
            continue
    return False


def wait_prompt(qmp: QMP, until: float) -> str:
    n = 0
    last_txt = ""
    paged = False
    while time.time() < until:
        n += 1
        dest = SHOT / f"wait-prompt-{n:03d}.png"
        qmp.screendump(dest)
        try:
            last_txt = glyph_text(dest)
        except Exception as e:
            last_txt = f"<ocr {e}>"
        dest.with_suffix(".txt").write_text(last_txt)
        lines = tail_lines(last_txt, 6)
        log(f"wait-prompt #{n} last={lines[-1:]!r}")
        if at_prompt(last_txt):
            log("prompt is back")
            return last_txt
        # Page the DolDoc so a new prompt below "More" becomes visible.
        # Safe while R3 is blocked in CommGetChar (it reads serial, not keys).
        if "More" in last_txt and time.time() >= PAGE_AFTER:
            if not paged:
                log("paging past More")
            try:
                qmp.send_qcodes("pgdn", hold=80)
            except Exception:
                try:
                    qmp.send_qcodes("spc", hold=80)
                except Exception as e:
                    log(f"page failed: {e}")
            paged = True
            time.sleep(1.0)
            continue
        time.sleep(15)
    raise TimeoutError(f"no prompt before deadline, last={tail_lines(last_txt, 4)!r}")


def type_and_wait(qmp: QMP, cmd: str, name: str, settle: float = 2.0, delay: float = 0.14) -> str:
    if not cmd.endswith("\n"):
        cmd += "\n"
    log(f"type {name}: {cmd[:100]!r}")
    qmp.type_text(cmd, delay=delay)
    time.sleep(settle)
    # wait until the command is no longer mid-line
    t = ""
    for i in range(12):
        p = SHOT / f"{name}{'' if i == 0 else f'-w{i}'}.png"
        qmp.screendump(p)
        t = glyph_text(p)
        p.with_suffix(".txt").write_text(t)
        if at_prompt(t):
            log(f"shot {name}: prompt")
            return t
        time.sleep(1.0)
    log(f"shot {name}: no prompt yet, continuing")
    return t


def main() -> int:
    SHOT.mkdir(parents=True, exist_ok=True)
    if not QMP_PATH.exists():
        log(f"missing qmp {QMP_PATH}")
        return 2
    qmp = QMP(QMP_PATH, timeout=60)
    try:
        shot(qmp, "100-continue-start")
        log("waiting for R3 CommGetChar timeout / prompt")
        wait_prompt(qmp, max(PROMPT_DEADLINE, time.time() + 60))
        shot(qmp, "101-prompt-back")

        type_and_wait(qmp, "Drv('C');", "102-drv-c", settle=1.5)
        t = type_and_wait(qmp, 'Dir("C:/Adam/Hermes");', "103-dir-hermes", settle=3.0)
        log("dir hermes tail: " + repr("\n".join(tail_lines(t, 12))[-500:]))
        t = type_and_wait(qmp, 'Dir("C:/Tmp/AfterOverlay.HC");', "104-dir-after", settle=2.0)
        t = type_and_wait(qmp, 'Dir("C:/Home/Once.HC");', "105-dir-once", settle=2.0)
        t = type_and_wait(qmp, 'Dir("C:/Kernel/KernelC.HH");', "106-dir-kernelc", settle=2.0)

        log("running AfterOverlay")
        type_and_wait(qmp, '#include "C:/Tmp/AfterOverlay.HC";', "107-afteroverlay", settle=4.0, delay=0.12)

        log("starting MakeDistro / BootDVDIns (slow under TCG)")
        type_and_wait(qmp, 'Cd("C:/");', "108-cd-root", settle=1.5)
        # Do not wait for prompt: MakeDistro runs until ISO is written
        qmp.type_text('#include "C:/Adam/Hermes/MakeDistro";\n', delay=0.12)
        time.sleep(3)
        shot(qmp, "109-makedistro-started")

        deadline = time.time() + 5400
        n = 0
        last = ""
        while time.time() < deadline:
            n += 1
            dest = SHOT / f"distro-{n:03d}.png"
            qmp.screendump(dest)
            try:
                last = glyph_text(dest)
            except Exception as e:
                last = f"<ocr {e}>"
            dest.with_suffix(".txt").write_text(last)
            low = last.lower()
            log(f"distro #{n} tail={tail_lines(last, 3)!r}")
            if "iso written" in low or "temple of hermes iso" in low or "hermes_iso_done" in low:
                log("MakeDistro finished (on-screen marker)")
                break
            time.sleep(20)
        else:
            # One last look, then still try extract — maybe the print scrolled off
            shot(qmp, "110-distro-timeout")
            log("WARNING: did not see ISO-written banner; will still try extract")

        shot(qmp, "111-iso-written")
        # Sync filesystem before shutdown
        if at_prompt(last) or "iso written" in last.lower():
            try:
                qmp.type_text("DskCacheInvalidate(Let2Drv('C'));\n", delay=0.12)
                time.sleep(3)
                qmp.type_text('Dir("C:/Tmp");\n', delay=0.12)
                time.sleep(3)
                shot(qmp, "112-tmp-dir")
            except Exception as e:
                log(f"sync/dir failed: {e}")
        time.sleep(2)
    finally:
        log("stopping VM")
        try:
            shot(qmp, "119-before-stop")
        except Exception:
            pass
        try:
            pid_s = (RUN / "hermes-build" / "pid").read_text().strip()
        except Exception:
            pid_s = ""
        try:
            stop_vm({"pid": pid_s or "0", "qmp": str(QMP_PATH)}, qmp)
        except Exception as e:
            log(f"stop_vm: {e}")
            try:
                qmp.quit()
            except Exception:
                pass
        try:
            qmp.close()
        except Exception:
            pass

    raw = RUN / "hermes-build.raw"
    log(f"converting {DISK} -> {raw}")
    if raw.exists():
        raw.unlink()
    subprocess.check_call(["qemu-img", "convert", "-O", "raw", str(DISK), str(raw)])
    try:
        fs = open_first_fat(raw)
        listing = "\n".join(fs.tree())
        (RUN / "fat-tree.txt").write_text(listing)
        log("fat tree (head):\n" + "\n".join(listing.splitlines()[:100]))
        fs.close()
    except Exception as e:
        log(f"fat tree failed: {e}")

    dest = DIST / ISO_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    candidates = [
        "/Tmp/TempleOfHermes.ISO.C",
        "/Tmp/TempleOfHermes.ISO.C.Z",
        "/Tmp/TEMPLEOF.ISO",
        "/Tmp/TempleOfHermes.ISO",
        "/Tmp/HERMES_ISO_DONE",
    ]
    last_err = None
    found = False
    for cand in candidates:
        try:
            if cand.endswith("HERMES_ISO_DONE"):
                # just check
                tmp = RUN / "HERMES_ISO_DONE"
                extract(raw, cand, tmp)
                log(f"done marker: {tmp.read_bytes()!r}")
                continue
            extract(raw, cand, dest)
            log(f"extracted {cand} -> {dest} ({dest.stat().st_size} bytes)")
            found = True
            last_err = None
            break
        except Exception as e:
            last_err = e
            log(f"extract {cand} failed: {e}")
    if not found:
        raise SystemExit(f"ISO extract failed: {last_err}")
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    (DIST / "SHA256SUMS").write_text(f"{digest}  {ISO_NAME}\n")
    log(f"SHA256 {digest}")
    raw.unlink(missing_ok=True)
    log("continue_iso finished")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"CONTINUE FAILED: {type(e).__name__}: {e}")
        raise
