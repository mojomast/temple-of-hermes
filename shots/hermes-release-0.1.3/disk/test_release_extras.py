#!/usr/bin/env python3
"""0.1.3 disk extras: HRPC structured error and home journal on C:.

Runs against a throwaway copy of the sealed disk image.  Boots with no CD,
proves Home.HC arrived from the image (never pushed), exercises HomeInit /
JournalAdd / ProjectSet / JournalTail / ProjectShow on C:, reboots the same
copy with no CD, and checks the journal and Src/ survived byte-identically and
that a further append works.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "shots" / "hermes-release-0.1.3" / "disk"))

from PIL import Image  # noqa: E402

from hrpc import Hrpc  # noqa: E402
from qemu_hermes import QMP, start_vm, stop_vm  # noqa: E402
import test_disk_image as tdi  # noqa: E402

ISO = ROOT / "dist" / "TempleOfHermes-0.1.3.ISO"
OUT = ROOT / "shots" / "hermes-release-0.1.3" / "disk"
WORK = ROOT / "run" / "release-disk-extras"
JOURNAL = "C:/Home/hermes/JOURNAL.TXT"
PROJECTS = "C:/Home/hermes/PROJECTS.TXT"
INIT_RESULT = "C:/Home/hermes/INIT-RESULT.TXT"
ISO_HOME = "T:/Adam/Hermes/Home.HC"
ISO_LOAD = "T:/Adam/Hermes/Load.HC"
LINE_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} .+$")


def log(msg: str, path: Path | None = None) -> None:
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with (path or (OUT / "extras.log")).open("a") as f:
        f.write(line + "\n")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode(payload: bytes) -> dict:
    try:
        return json.loads(payload.decode("utf-8", "replace"))
    except Exception:
        return {"raw": payload.decode("utf-8", "replace")}


def eval_ok(h: Hrpc, src: str, timeout: float = 120.0) -> dict:
    st, data = h.request("eval", src.encode(), timeout=timeout)
    body = decode(data)
    ok = (st == "ok" and isinstance(body, dict) and body.get("ok") == 1
          and not body.get("error"))
    return {"status": st, "body": body, "ok": bool(ok),
            "text": body.get("text", "") if isinstance(body, dict) else ""}


def pull(h: Hrpc, path: str, timeout: float = 30.0) -> tuple[bool, bytes]:
    st, data = h.request("pull", path.encode(), timeout=timeout)
    return st == "ok", data


def push(h: Hrpc, path: str, data: bytes, timeout: float = 30.0) -> dict:
    st, raw = h.request("push", path.encode() + b"\0" + data, timeout=timeout)
    return {"status": st, "body": decode(raw)}


def ping(h: Hrpc) -> dict:
    st, data = h.request("ping", b"", timeout=20)
    body = decode(data)
    return {"status": st, "pong": body.get("pong"),
            "version": body.get("version")}


def dir_has(h: Hrpc, parent_glob: str, name: str) -> bool:
    st, data = h.request("list", parent_glob.encode(), timeout=20)
    if st != "ok":
        return False
    try:
        entries = json.loads(data.decode())
    except Exception:
        return False
    return any(e.get("name", "").lower() == name.lower() and e.get("is_dir")
               for e in entries)


def journal_lines(data: bytes) -> list[str]:
    text = data.decode("utf-8", "replace").replace("\r\n", "\n")
    return [ln for ln in text.split("\n") if ln]


def check_journal_shape(rows: list[str], minimum: int) -> list[str]:
    errs: list[str] = []
    if len(rows) < minimum:
        errs.append(f"expected >= {minimum} journal lines, got {len(rows)}")
    for n, line in enumerate(rows, 1):
        if len(line) > 200:
            errs.append(f"line {n} longer than 200")
        if any(ord(c) < 32 or ord(c) == 127 for c in line):
            errs.append(f"line {n} has control character")
        if not LINE_RE.match(line):
            errs.append(f"line {n} not YYYY-MM-DD HH:MM <text>: {line[:60]!r}")
    return errs


def guest_timestamp_utc(line: str) -> datetime | None:
    try:
        return datetime.strptime(line[:16], "%Y-%m-%d %H:%M").replace(
            tzinfo=timezone.utc)
    except Exception:
        return None


def screenshot(q: QMP, dest: Path) -> dict:
    raw = WORK / ("raw-" + dest.name)
    q.screendump(raw)
    return tdi.to_palette(raw, dest)


def boot(image: Path, tag: str, timeout: float) -> tuple[object, QMP, Hrpc]:
    rundir = WORK / tag
    proc, m = tdi.start(rundir, image, "2G")
    q = QMP(m["qmp"], timeout=30)
    deadline = time.time() + timeout
    h = None
    while time.time() < deadline:
        time.sleep(2)
        try:
            h = Hrpc(m["com1"], timeout=10)
            h.request("ping", b"", timeout=10)
            ws = tdi.overlay_windows(h)
            if [w.get("title") for w in ws] == ["Hermes Apps"]:
                return proc, q, h
        except Exception:
            if h:
                h.close()
            h = None
    tdi.stop(proc, q)
    raise RuntimeError(f"{tag}: launcher/HRPC not ready")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=Path, required=True)
    ap.add_argument("--timeout", type=float, default=75.0)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    (OUT / "extras.log").write_text("")

    def sha_file(p: Path) -> str:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    source_sha = sha_file(args.image)
    image = WORK / "extras.qcow2"
    shutil.copyfile(args.image, image)
    result: dict = {"image": str(args.image), "image_sha256": source_sha,
                    "checks": [], "phase1": {}, "phase2": {}}

    def check(name: str, passed: bool, detail: str = "") -> None:
        result["checks"].append({"name": name, "passed": bool(passed),
                                 "detail": detail})
        log(f"{name}: {'PASS' if passed else 'FAIL'} {detail}")

    log(f"image copy {image} from {args.image}")
    try:
        # ---------------- phase 1: image provenance + journal write ----------
        proc, q, h = boot(image, "phase1", args.timeout)
        try:
            check("launcher_no_cd", True, "Hermes Apps only")
            home_ok, home_bytes = pull(h, "C:/Adam/Hermes/Home.HC")
            local_home = (ROOT / "Adam/Hermes/Home.HC").read_bytes()
            check("home_hc_from_image", home_ok and home_bytes == local_home,
                  f"{len(home_bytes)} bytes" if home_ok else "pull failed")
            load_ok, load_bytes = pull(h, "C:/Adam/Hermes/Load.HC")
            inc = b'#include "Home"' in load_bytes
            check("load_inc_home_from_image", load_ok and inc,
                  f"{len(load_bytes)} bytes include={inc}" if load_ok else
                  "pull failed")
            result["phase1"]["home_hc_sha256"] = sha(home_bytes) if home_ok else None
            result["phase1"]["load_hc_sha256"] = sha(load_bytes) if load_ok else None

            # No file was pushed; HomeInit only exists if the image compiled
            # Adam/Hermes/Home.HC into the daemon's global symbol table.
            ev = eval_ok(
                h,
                'U8 *r;r=HomeInit("hermes",\'C\');'
                f'FileWrite("{INIT_RESULT}",r,StrLen(r));Free(r);\n')
            ok_init, init_bytes = pull(h, INIT_RESULT)
            check("homeinit_loaded_not_pushed",
                  ev["ok"] and ok_init and init_bytes.startswith(b"OK "),
                  f"eval={ev['ok']} init={init_bytes[:80]!r}")
            check("homeinit_created_layout",
                  dir_has(h, "C:/Home/hermes/*", "Src"),
                  "C:/Home/hermes/Src present")
            src_marker = b"src-survives\n"
            push(h, "C:/Home/hermes/Src/KEEP.TXT", src_marker)
            ok_src, src_bytes = pull(h, "C:/Home/hermes/Src/KEEP.TXT")
            check("src_marker_written", ok_src and src_bytes == src_marker,
                  f"{len(src_bytes)} bytes" if ok_src else "pull failed")

            ev = eval_ok(
                h,
                'U8 *r;'
                'r=JournalAdd("release journal entry one");Free(r);'
                'r=JournalAdd("release journal entry two");Free(r);'
                'r=ProjectSet("Temple of Hermes 0.1.3",'
                '"Verify home journal on C");Free(r);\n')
            check("journal_writes", ev["ok"], str(ev["body"])[:160])
            ok_j, journal1 = pull(h, JOURNAL)
            ok_p, projects1 = pull(h, PROJECTS)
            rows1 = journal_lines(journal1) if ok_j else []
            jerrs = check_journal_shape(rows1, 2)
            check("journal_readback", ok_j and not jerrs,
                  "; ".join(jerrs) if jerrs else f"{len(rows1)} lines")
            check("journal_entries",
                  len(rows1) >= 2 and rows1[0].endswith("release journal entry one")
                  and rows1[1].endswith("release journal entry two"),
                  repr(rows1[-2:]))
            check("projects_readback",
                  ok_p and projects1 ==
                  b"Current: Temple of Hermes 0.1.3\n"
                  b"Next: Verify home journal on C\n",
                  repr(projects1[-120:]))
            ts = guest_timestamp_utc(rows1[0]) if rows1 else None
            skew = abs((datetime.now(timezone.utc) - ts).total_seconds()) \
                if ts else None
            check("journal_timestamp_utc", skew is not None and skew < 600,
                  f"guest={rows1[0][:16] if rows1 else '?'} skew_s={skew}")
            result["phase1"].update({
                "journal_sha256": sha(journal1) if ok_j else None,
                "journal_lines": rows1,
                "journal_bytes": len(journal1) if ok_j else None,
                "projects_sha256": sha(projects1) if ok_p else None,
                "projects_bytes": len(projects1) if ok_p else None,
                "timestamp_skew_seconds": skew,
            })
            # Keep the exact bytes for the byte-identical reboot comparison.
            (WORK / "journal-phase1.bin").write_bytes(journal1 if ok_j else b"")
            (WORK / "projects-phase1.bin").write_bytes(projects1 if ok_p else b"")

            # 0.1.3 auto-creates missing parent directories on a writable
            # drive.  Record that positive behavior; the read-only and
            # missing-dir error bodies are exercised in phase 3 on T:.
            auto = push(h, "C:/Home/RELEASE-AUTO-DIR/child.txt", b"auto")
            check("writable_missing_parent_autocreate",
                  auto["status"] == "ok", f"status={auto['status']}")
            result["phase1"]["writable_autocreate"] = {
                "status": auto["status"], "body": auto.get("body")}
            p = ping(h)
            check("ping_after_phase1", p["status"] == "ok" and p["pong"] == 1,
                  f"version={p['version']}")
            result["phase1"]["ping"] = p
            result["phase1"]["shot"] = screenshot(
                q, OUT / "journal-phase1.png")
        finally:
            h.close()
            tdi.stop(proc, q)

        # ---------------- phase 2: reboot same disk copy --------------------
        proc, q, h = boot(image, "phase2", args.timeout)
        try:
            ok_j2, journal2 = pull(h, JOURNAL)
            ok_p2, projects2 = pull(h, PROJECTS)
            j1 = (WORK / "journal-phase1.bin").read_bytes()
            p1 = (WORK / "projects-phase1.bin").read_bytes()
            check("journal_survived_reboot",
                  ok_j2 and journal2 == j1 and bool(j1),
                  f"{len(journal2)} bytes sha={sha(journal2)}")
            check("projects_survived_reboot",
                  ok_p2 and projects2 == p1 and bool(p1),
                  f"{len(projects2)} bytes sha={sha(projects2)}")
            ok_src2, src_bytes2 = pull(h, "C:/Home/hermes/Src/KEEP.TXT")
            check("src_survived_reboot",
                  dir_has(h, "C:/Home/hermes/*", "Src")
                  and ok_src2 and src_bytes2 == b"src-survives\n",
                  f"Src/ present, marker {len(src_bytes2)} bytes byte-identical")
            rows2 = journal_lines(journal2) if ok_j2 else []
            result["phase2"] = {
                "journal_sha256": sha(journal2) if ok_j2 else None,
                "journal_lines": rows2,
                "projects_sha256": sha(projects2) if ok_p2 else None,
            }

            ev = eval_ok(
                h,
                'U8 *r;r=HomeInit("hermes",\'C\');Free(r);'
                'r=JournalAdd("post reboot append");Free(r);\n')
            check("homeinit_after_reboot", ev["ok"], str(ev["body"])[:160])
            ok_j3, journal3 = pull(h, JOURNAL)
            rows3 = journal_lines(journal3) if ok_j3 else []
            check("append_after_reboot",
                  ev["ok"] and ok_j3 and journal3.startswith(j1)
                  and len(rows3) == len(rows2) + 1
                  and rows3[-1].endswith("post reboot append"),
                  f"{len(rows2)} -> {len(rows3)} lines")
            check("journal_shape_after_append",
                  not check_journal_shape(rows3, len(rows2) + 1),
                  "; ".join(check_journal_shape(rows3, len(rows2) + 1)))
            proj_ok = eval_ok(h, "ProjectShow();\n")
            check("project_show_after_reboot", proj_ok["ok"],
                  str(proj_ok["body"])[:120])
            result["phase2"]["journal_after_append_sha256"] = sha(journal3)
            p = ping(h)
            check("ping_after_phase2", p["status"] == "ok" and p["pong"] == 1,
                  f"version={p['version']}")
            result["phase2"]["ping"] = p
            result["phase2"]["shot"] = screenshot(
                q, OUT / "journal-phase2.png")
        finally:
            h.close()
            tdi.stop(proc, q)

        # ---------------- phase 3: read-only CD errors ----------------------
        # Drive C still boots (order=c); the release ISO is attached only as
        # read-only T: so the 0.1.3 guards can answer missing_dir/read_only.
        meta = start_vm("release-extras-cd", ISO, image, memory="2G",
                        boot="c")
        q3 = QMP(Path(meta["qmp"]), timeout=30)
        h3 = None
        try:
            deadline = time.time() + args.timeout
            while time.time() < deadline:
                time.sleep(2)
                try:
                    h3 = Hrpc(meta["com1"], timeout=10)
                    h3.request("ping", b"", timeout=10)
                    ws = tdi.overlay_windows(h3)
                    if [w.get("title") for w in ws] == ["Hermes Apps"]:
                        break
                except Exception:
                    if h3:
                        h3.close()
                    h3 = None
            if h3 is None:
                raise RuntimeError("phase3: launcher/HRPC not ready")
            miss = push(h3, "T:/Hermes/Apps/__HERMES_NO_SUCH_DIR__/x.txt",
                        b"dummy")
            mcode = (miss.get("body") or {}).get("code") or \
                (miss.get("body") or {}).get("error") or ""
            ro = push(h3, "T:/Hermes/Apps/Launcher/release-readonly.txt",
                      b"dummy")
            rcode = (ro.get("body") or {}).get("code") or \
                (ro.get("body") or {}).get("error") or ""
            p3 = ping(h3)
            check("iso_missing_dir_structured",
                  miss["status"] == "err" and mcode == "missing_dir"
                  and p3["status"] == "ok" and p3["pong"] == 1,
                  f"status={miss['status']} code={mcode!r}")
            check("iso_read_only_structured",
                  ro["status"] == "err" and rcode == "read_only"
                  and p3["status"] == "ok" and p3["pong"] == 1,
                  f"status={ro['status']} code={rcode!r}")
            result["phase3"] = {
                "missing_dir": {"status": miss["status"], "code": mcode},
                "read_only": {"status": ro["status"], "code": rcode},
                "ping_after": p3,
            }
            result["phase3"]["shot"] = screenshot(
                q3, OUT / "errors-phase3.png")
        finally:
            if h3:
                h3.close()
            try:
                stop_vm(meta, q3)
            except Exception:
                pass
            try:
                q3.close()
            except Exception:
                pass
    finally:
        after = sha_file(args.image)
        result["image_sha256_after"] = after
        result["source_unchanged"] = after == source_sha
        passed = sum(1 for c in result["checks"] if c["passed"])
        result["passed"] = passed
        result["total"] = len(result["checks"])
        result["ok"] = passed == len(result["checks"]) and \
            result["source_unchanged"]
        (OUT / "extras.json").write_text(json.dumps(result, indent=2) + "\n")
        log(f"extras: {passed}/{len(result['checks'])} "
            f"source_unchanged={result['source_unchanged']}")
    print(json.dumps({"ok": result["ok"], "passed": result["passed"],
                      "total": result["total"]}))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
