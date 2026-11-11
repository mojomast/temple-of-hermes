#!/usr/bin/env python3
"""Host QEMU regression for the Hermes home directory helpers.

Boots the official Temple of Hermes v0.1.2 ISO live (sha256 verified),
creates the B: home directories, pushes Adam/Hermes/Home.HC and
Adam/Hermes/HomeTest.HC, runs them through the HRPC eval op, pulls the
result, JOURNAL.TXT and PROJECTS.TXT back, and asserts the layout contract
read by the host plugin's session_start reader.

PIL is used only to validate the 640x480 screendumps.  `--static` runs the
source and parser checks without QEMU.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

OUT = ROOT / "shots" / "hermes-home-0.1.3"
RAW = ROOT / "shots" / "_raw" / "hermes-home-0.1.3"
LOG = OUT / "home-journal.log"
SLOG = OUT / "home-journal-static.log"
ISO_NAME = "TempleOfHermes-0.1.2.ISO"
ISO_SHA256 = "9afc98ed2bb15a3ff26ebaca12ea392079292df6667b3c1c527fdd30d80cdb13"
DEFAULT_ISO = ROOT / "dist" / ISO_NAME
HANDLE = "hermes"
HOME = f"B:/Home/{HANDLE}"
JOURNAL = f"{HOME}/JOURNAL.TXT"
PROJECTS = f"{HOME}/PROJECTS.TXT"
RESULT = f"{HOME}/HOME-TEST.TXT"
LINE_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} .+$")
MAX_LINE = 200
BAD_TEXT = ("Unhandled Exception", "DEBUGGER", "Debugger", "RedSea",
            "DirContextNew")


def log(msg: str, dest: Path | None = None) -> None:
    line = (time.strftime("%H:%M:%S ") + msg).rstrip()
    print(line, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with (dest or LOG).open("a") as f:
        f.write(line + "\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode(payload: bytes) -> dict:
    try:
        return json.loads(payload.decode("utf-8", "replace"))
    except Exception:
        return {"raw": payload.decode("utf-8", "replace")}


def clean_lines(text: str) -> list[str]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def validate_journal(text: str, expected: int = 3) -> list[str]:
    lines = clean_lines(text)
    errors: list[str] = []
    if len(lines) != expected:
        errors.append(f"expected {expected} journal lines, got {len(lines)}")
    for n, line in enumerate(lines, 1):
        if len(line) > MAX_LINE:
            errors.append(f"line {n} is {len(line)} chars (> {MAX_LINE})")
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in line):
            errors.append(f"line {n} has a control character")
        if "\t" in line:
            errors.append(f"line {n} has a tab")
        if not LINE_RE.match(line):
            errors.append(f"line {n} does not match YYYY-MM-DD HH:MM <text>")
    return errors


def validate_projects(text: str) -> list[str]:
    lines = clean_lines(text)
    errors: list[str] = []
    if len(lines) != 2:
        errors.append(f"expected 2 project lines, got {len(lines)}")
    for n, line in enumerate(lines, 1):
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in line):
            errors.append(f"line {n} has a control character")
    if len(lines) >= 1 and not lines[0].startswith("Current: "):
        errors.append("line 1 is not 'Current: <project>'")
    if len(lines) >= 2 and not lines[1].startswith("Next: "):
        errors.append("line 2 is not 'Next: <next step>'")
    return errors




def balanced(text: str) -> tuple[bool, str]:
    pairs = {"{": "}", "(": ")", "[": "]"}
    stack: list[str] = []
    i = 0
    in_str = False
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif text.startswith("//", i):
                j = text.find("\n", i)
                i = len(text) if j == -1 else j
                continue
            elif ch in pairs:
                stack.append(pairs[ch])
            elif ch in "})]":
                if not stack or stack.pop() != ch:
                    return False, f"unexpected {ch} at {i}"
        i += 1
    if in_str:
        return False, "unterminated string"
    if stack:
        return False, "unclosed " + "".join(stack)
    return True, ""

def static_checks() -> dict:
    checks: list[dict] = []

    def add(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
        log(f"static {name}: {'PASS' if passed else 'FAIL'} {detail}", SLOG)

    home = (ROOT / "Adam/Hermes/Home.HC").read_text()
    test = (ROOT / "Adam/Hermes/HomeTest.HC").read_text()
    load = (ROOT / "Adam/Hermes/Load.HC").read_text()
    doc = ROOT / "docs/HOME-DIR.md"
    doc_text = doc.read_text() if doc.is_file() else ""

    for fn in ("HomeInit", "JournalAdd", "JournalTail", "ProjectSet",
               "ProjectShow", "HomeDir"):
        add(f"home_defines_{fn}", f"U8 *{fn}(" in home)
    add("home_line_max_200", "#define HERMES_HOME_LINE_MAX 200" in home)
    add("home_current_next", '"Current: %s\\nNext: %s\\n"' in home)
    add("home_src_dir", "/Src" in home)
    add("home_writable_check", "DrvIsWritable" in home and
        "drive_not_writable" in home)
    add("home_control_strip", "*s>=32" in home and "127" in home)
    add("test_uses_journal_tail", "JournalTail(3)" in test)
    add("test_uses_project_set", 'ProjectSet("Temple of Hermes"' in test)
    add("test_no_c_error", "no_c_error" in test)
    add("load_one_home_include", load.count('#include "Home"') == 1)
    hb, hd = balanced(home)
    add("home_syntax_balanced", hb, hd)
    tb, td = balanced(test)
    add("test_syntax_balanced", tb, td)
    add("home_include_guard", "#ifndef HERMES_HOME_HC" in home and
        "#endif" in home)
    add("doc_exists", doc.is_file() and len(doc_text) > 500)
    for needle in ("C:/Home/<handle>/", "JOURNAL.TXT", "PROJECTS.TXT",
                   "Current:", "Next:", "B: is RAM only",
                   "read-only", "session_start"):
        add(f"doc_mentions_{needle.split()[0]}", needle in doc_text, needle)

    fixture_journal = (
        "2026-11-11 09:15 session one\n"
        "2026-11-11 09:15 sessiontwonext\n"
        "2026-11-11 09:15 " + "X" * 183 + "\n"
    )
    errors = validate_journal(fixture_journal, 3)
    add("parser_accepts_contract", not errors, "; ".join(errors))
    bad = "2026-11-11 09:15 has\ttab\n" + "2026-11-11 09:15 " + "Y" * 200 + "\n"
    add("parser_rejects_bad", bool(validate_journal(bad, 2)))
    fixture_projects = "Current: Temple of Hermes\nNext: Write HOME-DIR docs\n"
    perrors = validate_projects(fixture_projects)
    add("parser_projects", not perrors, "; ".join(perrors))

    passed = sum(1 for c in checks if c["passed"])
    result = {
        "mode": "static",
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "ok": passed == len(checks),
        "finished": time.time(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "home-journal-static.json").write_text(
        json.dumps(result, indent=2) + "\n")
    log(f"static matrix: {passed}/{len(checks)}", SLOG)
    return result


class Guest:
    def __init__(self, cli):
        self.cli = cli

    def eval(self, src: str, timeout: float = 180.0) -> dict:
        st, data = self.cli.request("eval", src.encode("utf-8"), timeout=timeout)
        body = decode(data)
        text = body.get("text", "") if isinstance(body, dict) else ""
        ok = (st == "ok" and isinstance(body, dict) and body.get("ok") == 1
              and not body.get("error"))
        return {"status": st, "body": body, "text": text, "ok": bool(ok)}

    def push(self, path: str, data: bytes, timeout: float = 60.0) -> dict:
        st, raw = self.cli.request(
            "push", path.encode("utf-8") + b"\0" + data, timeout=timeout)
        body = decode(raw)
        ok = st == "ok" and isinstance(body, dict) and body.get("ok") == 1
        return {"status": st, "body": body, "ok": bool(ok)}

    def pull(self, path: str, timeout: float = 60.0) -> dict:
        st, data = self.cli.request("pull", path.encode("utf-8"),
                                    timeout=timeout)
        return {"status": st, "data": data, "ok": st == "ok"}


def palette_check(src: Path, dest: Path) -> dict:
    from PIL import Image
    im = Image.open(src).convert("RGB")
    if im.size != (640, 480):
        raise ValueError(f"{src.name} is {im.size}, not 640x480")
    colors = im.getcolors(maxcolors=1 << 20) or []
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest)
    return {"size": list(im.size), "colors": len(colors),
            "png": dest.name}


def run_vm(iso: Path) -> dict:
    from PIL import Image  # noqa: F401  (qemu_hermes imports it too)
    from hrpc import Hrpc
    from qemu_hermes import QMP, start_vm, stop_vm

    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    log(f"iso {iso.name} sha256={sha256_file(iso)}")
    meta = start_vm("home-journal", iso, None, memory="2G", boot="d")
    qmp = QMP(Path(meta["qmp"]), timeout=60)
    cli = Hrpc(Path(meta["com1"]), timeout=60, log=OUT / "home-journal-com1.log")
    results: dict = {
        "mode": "qemu",
        "iso": iso.relative_to(ROOT).as_posix() if iso.is_relative_to(ROOT)
        else iso.name,
        "iso_sha256": sha256_file(iso),
        "checks": [],
        "shots": [],
    }
    rc = 1

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append(
            {"name": name, "passed": bool(passed), "detail": detail})
        log(f"{name}: {'PASS' if passed else 'FAIL'} {detail}")

    try:
        log("waiting for HBEACON")
        beacon = cli.wait_beacon(timeout=180)
        log(f"beacon: {beacon}")
        results["beacon"] = beacon
        check("beacon", beacon.startswith("HBEACON TempleOfHermes/"), beacon)

        shot = RAW / "01-home-journal-boot.png"
        qmp.screendump(shot)
        results["shots"].append(palette_check(
            shot, OUT / "01-home-journal-boot.png"))
        log("boot screenshot checked with PIL")

        g = Guest(cli)
        setup = (
            'try\n'
            '{\n'
            '  DirMk("B:/Home");\n'
            '  DirMk("B:/Home/hermes");\n'
            '  DirMk("B:/Home/hermes/Src");\n'
            '  if (FileFind("B:/Home/hermes/JOURNAL.TXT"))\n'
            '    Del("B:/Home/hermes/JOURNAL.TXT");\n'
            '  if (FileFind("B:/Home/hermes/PROJECTS.TXT"))\n'
            '    Del("B:/Home/hermes/PROJECTS.TXT");\n'
            '  if (FileFind("B:/Home/hermes/HOME-TEST.TXT"))\n'
            '    Del("B:/Home/hermes/HOME-TEST.TXT");\n'
            '  "HOME DIRS OK";\n'
            '}\n'
            'catch\n'
            '{\n'
            '  Fs->catch_except=TRUE;\n'
            '  "HOME DIRS FAILED";\n'
            '}\n'
        )
        r = g.eval(setup)
        check("b_dirs", r["ok"] and "HOME DIRS OK" in r["text"],
              r["text"][-200:])

        home_src = (ROOT / "Adam/Hermes/Home.HC").read_bytes()
        test_src = (ROOT / "Adam/Hermes/HomeTest.HC").read_bytes()
        r = g.push(f"{HOME}/Home.HC", home_src)
        check("push_home", r["ok"], str(r["body"])[:200])
        r = g.push(f"{HOME}/HomeTest.HC", test_src)
        check("push_home_test", r["ok"], str(r["body"])[:200])

        r = g.eval(
            '#include "B:/Home/hermes/Home.HC";\n'
            '"HOME HC OK";\n', timeout=180)
        check("compile_home", r["ok"] and "HOME HC OK" in r["text"],
              r["text"][-300:])

        run = g.eval('#include "B:/Home/hermes/HomeTest.HC";\n', timeout=300)
        results["run_text"] = run["text"]
        results["run_body"] = run["body"]
        bad = [w for w in BAD_TEXT if w.lower() in run["text"].lower()]
        check("run_home_test", run["ok"] and "HOME TEST DONE" in run["text"],
              f"bad={bad} tail={run['text'][-300:]}")
        check("no_debugger", not bad, str(bad))

        pulled = {k: g.pull(v) for k, v in
                  (("result", RESULT), ("journal", JOURNAL),
                   ("projects", PROJECTS))}
        for key, rec in pulled.items():
            check(f"pull_{key}", rec["ok"],
                  "" if rec["ok"] else rec["status"])
        result_text = pulled["result"]["data"].decode("utf-8", "replace") \
            if pulled["result"]["ok"] else ""
        journal_text = pulled["journal"]["data"].decode("utf-8", "replace") \
            if pulled["journal"]["ok"] else ""
        projects_text = pulled["projects"]["data"].decode("utf-8", "replace") \
            if pulled["projects"]["ok"] else ""
        results["result_text"] = result_text
        results["journal_text"] = journal_text
        results["projects_text"] = projects_text

        check("result_pass", "HERMES HOME TEST PASS" in result_text
              and "FAIL" not in result_text, result_text[-300:])

        jerrors = validate_journal(journal_text, 3)
        check("journal_format", not jerrors, "; ".join(jerrors))
        jlines = clean_lines(journal_text)
        check("journal_session_one", bool(jlines) and
              jlines[0].endswith("session one"),
              jlines[0][-80:] if jlines else "")
        check("journal_control_stripped", len(jlines) > 1 and
              jlines[1].endswith("sessiontwonext"),
              jlines[1][-80:] if len(jlines) > 1 else "")
        check("journal_truncated_200", len(jlines) > 2 and
              len(jlines[2]) == MAX_LINE and
              jlines[2][17:] == "X" * 183,
              f"len={len(jlines[2])}" if len(jlines) > 2 else "missing")

        perrors = validate_projects(projects_text)
        check("projects_format", not perrors, "; ".join(perrors))
        check("projects_values",
              projects_text ==
              "Current: Temple of Hermes\nNext: Write HOME-DIR docs\n",
              projects_text[-200:])

        tail = g.eval('"%s",JournalTail(3);\n')
        check("journal_tail", tail["ok"] and "session one" in tail["text"]
              and "sessiontwonext" in tail["text"], tail["text"][-300:])

        cprobe = g.eval(
            'try\n'
            '{\n'
            "  if (Let2Drv('C',FALSE))\n"
            '    "C-PRESENT";\n'
            '  else\n'
            '    "C-ABSENT";\n'
            '}\n'
            'catch\n'
            '{\n'
            '  Fs->catch_except=TRUE;\n'
            '  "C-ABSENT";\n'
            '}\n')
        c_absent = "C-ABSENT" in cprobe["text"]
        results["c_absent"] = c_absent
        log(f"C: present={not c_absent}")
        if c_absent:
            no_c = g.eval('"%s",HomeInit(NULL,\'C\');\n')
            ntext = no_c["text"]
            cbad = [w for w in BAD_TEXT if w.lower() in ntext.lower()]
            check("no_c_error", no_c["ok"] and ntext.strip().startswith("ERR ")
                  and not cbad, f"text={ntext[-200:]!r} bad={cbad}")
        else:
            check("no_c_error", True, "skipped: C: is present on this boot")

        shot = RAW / "02-home-journal-run.png"
        qmp.screendump(shot)
        results["shots"].append(palette_check(
            shot, OUT / "02-home-journal-run.png"))
        log("run screenshot checked with PIL")

        passed = sum(1 for c in results["checks"] if c["passed"])
        results["passed"] = passed
        results["total"] = len(results["checks"])
        results["ok"] = passed == len(results["checks"])
        rc = 0 if results["ok"] else 1
        log(f"home matrix: {passed}/{len(results['checks'])}")
    finally:
        results["finished"] = time.time()
        (OUT / "home-journal.json").write_text(
            json.dumps(results, indent=2) + "\n")
        try:
            cli.close()
        except Exception:
            pass
        try:
            stop_vm(meta, qmp)
        except Exception:
            pass
        try:
            qmp.close()
        except Exception:
            pass
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--iso", type=Path, default=None,
                    help=f"v0.1.2 ISO (default {DEFAULT_ISO})")
    ap.add_argument("--static", action="store_true",
                    help="source and parser checks only; no QEMU")
    ap.add_argument("--skip-sha256", action="store_true",
                    help="do not verify the official ISO digest")
    args = ap.parse_args()

    LOG.parent.mkdir(parents=True, exist_ok=True)

    if args.static:
        SLOG.write_text("")
        res = static_checks()
        print(json.dumps({"mode": "static", "ok": res["ok"],
                          "passed": res["passed"], "total": res["total"]}))
        return 0 if res["ok"] else 1

    LOG.write_text("")
    iso = args.iso or Path(os.environ.get("TOH_HOME_ISO", DEFAULT_ISO))
    missing = []
    if shutil.which("qemu-system-x86_64") is None:
        missing.append("qemu-system-x86_64")
    try:
        import PIL  # noqa: F401
    except Exception:
        missing.append("PIL")
    if not iso.is_file():
        missing.append(iso.name)
    if missing:
        log("prerequisites missing: " + ", ".join(missing))
        log("run with --static for source/parser checks")
        return 2

    digest = sha256_file(iso)
    if digest != ISO_SHA256 and not args.skip_sha256:
        log(f"ISO sha256 mismatch: {digest} != {ISO_SHA256}")
        return 2
    if digest != ISO_SHA256:
        log(f"ISO sha256 not the official value: {digest}")

    res = run_vm(iso)
    print(json.dumps({"mode": "qemu", "ok": res.get("ok"),
                      "passed": res.get("passed"),
                      "total": res.get("total")}))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
