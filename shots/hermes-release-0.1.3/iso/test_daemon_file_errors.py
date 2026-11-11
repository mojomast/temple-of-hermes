#!/usr/bin/env python3
"""File-error acceptance for TempleOfHermes-0.1.3 on the live CD.

Every case must produce a structured HRPL err (or a documented success for
the writable B: RAM drive), and a follow-up ping must still answer HRPL ok.
PIL/OCR only; no screenshot is opened or shown in-model.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from PIL import Image  # noqa: E402

from hrpc import Hrpc  # noqa: E402
from qemu_hermes import QMP, glyph_text, start_vm, stop_vm  # noqa: E402

ISO = ROOT / "dist" / "TempleOfHermes-0.1.3.ISO"
OUT = ROOT / "shots" / "hermes-release-0.1.3" / "iso"
RAW = ROOT / "shots" / "_raw" / "hermes-release-0.1.3" / "iso"
MAX_PAYLOAD = 262144

PALETTE = [
    (0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170),
    (170, 0, 0), (170, 0, 170), (170, 85, 0), (170, 170, 170),
    (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255),
    (255, 85, 85), (255, 85, 255), (255, 255, 85), (255, 255, 255),
]

BAD_OCR = (
    "Unhandled Exception", "Unhandled", "DEBUGGER", "Debugger",
    "DirContextNew", "FileWrite ERROR", "RedSea",
)

MISSING_PATH = "T:/Hermes/Apps/__HERMES_NO_SUCH_DIR__/marker.txt"
CD_PATH = "T:/Hermes/Apps/Launcher/hermes-daemon-0.1.3-marker.txt"
RAM_PATH = "B:/Tmp/hermes-daemon-fix-0.1.3-marker.txt"
BAD_DRIVE_PATH = "Q:/Hermes/marker.txt"
RAM_BODY = b"dummy marker"


def log(msg: str) -> None:
    line = (time.strftime("%H:%M:%S ") + msg).rstrip()
    print(line, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "file-errors.log").open("a") as f:
        f.write(line + "\n")


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
                        d = ((rgb[0] - c[0]) ** 2 + (rgb[1] - c[1]) ** 2
                             + (rgb[2] - c[2]) ** 2)
                        if d < bd:
                            bd, best = d, k
                    i = best
                cache[rgb] = i
            op[x, y] = i
    out.putpalette([c for rgb in PALETTE for c in rgb] + [0] * (768 - 48))
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    used = len(set(out.getdata()))
    return {"size": [640, 480], "mode": out.mode, "used": used}


def decode(payload: bytes) -> dict:
    try:
        return json.loads(payload.decode("utf-8", "replace"))
    except Exception:
        return {"raw": payload.decode("utf-8", "replace")}


def ping(cli: Hrpc, timeout: float = 20.0) -> dict:
    st, data = cli.request("ping", b"", timeout=timeout)
    body = decode(data)
    return {
        "status": st,
        "pong": body.get("pong"),
        "version": body.get("version"),
        "payload": body,
    }


def request_header_only(cli: Hrpc, op: str, length: int,
                        timeout: float = 20.0) -> tuple[str, bytes]:
    """Send an HREQ header with an oversized declared length, no body.

    The daemon must reject on the header before reading a payload, leaving
    the COM1 stream clean for the next request.
    """
    req_id = cli.next_id
    cli.next_id += 1
    header = f"HREQ {req_id} {op} {length}\n".encode("ascii")
    cli._log(">>", header)
    cli.sock.sendall(header)
    cli._pending_rpl = None
    cli._pending_payload = None
    cli._pending_status = None
    deadline = time.time() + timeout
    while time.time() < deadline:
        chunk = cli._recv_some(min(1.0, max(0.05, deadline - time.time())))
        if chunk:
            cli.buf += chunk
        cli._consume_async()
        if cli._pending_rpl is not None:
            status = cli._pending_status or "ok"
            data = cli._pending_payload or b""
            cli._pending_rpl = None
            return status, data
    raise TimeoutError(f"no HRPL for oversized {op} header id={req_id}")


def run_case(cli: Hrpc, name: str, op: str, path: str, body: bytes,
             accepted: tuple[str, ...], must_ok: bool = False) -> dict:
    payload = path.encode("utf-8") + b"\0" + body
    st, data = cli.request(op, payload, timeout=30)
    body_obj = decode(data)
    code = body_obj.get("code") or body_obj.get("error") or ""
    ok = False
    if must_ok:
        ok = st == "ok" and bool(body_obj.get("ok")) and code == ""
    else:
        ok = st == "err" and code in accepted
    rec = {
        "case": name,
        "op": op,
        "path": path,
        "status": st,
        "code": code,
        "accepted": list(accepted),
        "must_ok": must_ok,
        "payload": body_obj,
        "ok": ok,
    }
    p = ping(cli)
    rec["ping_after"] = p
    rec["ok"] = bool(ok and p["status"] == "ok" and p["pong"] == 1)
    log(f"{name}: status={st} code={code!r} ping={p['status']} "
        f"version={p['version']} -> {'PASS' if rec['ok'] else 'FAIL'}")
    return rec


def main() -> int:
    if not ISO.is_file():
        log(f"missing ISO {ISO}")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    meta = start_vm("daemon-fix-errors", ISO, None, memory="2G", boot="d")
    qmp = QMP(Path(meta["qmp"]), timeout=60)
    cli = Hrpc(Path(meta["com1"]), timeout=60, log=OUT / "file-errors-com1.log")
    results: dict = {"iso": ISO.relative_to(ROOT).as_posix(), "cases": []}
    rc = 1
    try:
        log("waiting for HBEACON")
        beacon = cli.wait_beacon(timeout=120)
        log(f"beacon: {beacon}")
        results["beacon"] = beacon

        cases = []
        cases.append(run_case(cli, "missing_dir", "push", MISSING_PATH,
                              b"dummy", ("missing_dir",)))
        cases.append(run_case(
            cli, "released_bug_path", "push",
            "C:/Hermes/Apps/HermesBBS/token.txt", b"dummy",
            ("bad_drive", "missing_dir", "read_only")))
        cases.append(run_case(cli, "read_only_cd", "push", CD_PATH,
                              b"dummy", ("read_only",)))
        ram = run_case(cli, "ram_write", "push", RAM_PATH, RAM_BODY,
                       ("",), must_ok=True)
        cases.append(ram)
        if ram["ok"]:
            st, data = cli.request("pull", RAM_PATH.encode(), timeout=30)
            cases.append({
                "case": "ram_pull", "op": "pull", "path": RAM_PATH,
                "status": st, "code": "",
                "payload": {"bytes": len(data), "matches": data == RAM_BODY},
                "ok": st == "ok" and data == RAM_BODY,
            })
            cases[-1]["ping_after"] = ping(cli)
            cases[-1]["ok"] = bool(cases[-1]["ok"] and
                                   cases[-1]["ping_after"]["status"] == "ok")
            log(f"ram_pull: status={st} bytes={len(data)} "
                f"matches={data == RAM_BODY} -> "
                f"{'PASS' if cases[-1]['ok'] else 'FAIL'}")

        st, data = request_header_only(cli, "push", MAX_PAYLOAD + 1, timeout=30)
        body_obj = decode(data)
        code = body_obj.get("code") or body_obj.get("error") or ""
        p = ping(cli)
        rec = {
            "case": "huge_payload", "op": "push",
            "path": "", "status": st, "code": code,
            "accepted": ["too_large"], "declared_len": MAX_PAYLOAD + 1,
            "payload": body_obj, "ping_after": p,
            "ok": st == "err" and code == "too_large" and
                  p["status"] == "ok" and p["pong"] == 1,
        }
        cases.append(rec)
        log(f"huge_payload: status={st} code={code!r} ping={p['status']} -> "
            f"{'PASS' if rec['ok'] else 'FAIL'}")

        cases.append(run_case(cli, "bad_drive", "push", BAD_DRIVE_PATH,
                              b"dummy", ("bad_drive",)))
        results["cases"] = cases

        # Final screen must not show a debugger or exception string.
        shot = RAW / "file-errors-after.png"
        qmp.screendump(shot)
        text = glyph_text(shot)
        bad = [w for w in BAD_OCR if w.lower() in text.lower()]
        info = to_palette(shot, OUT / "file-errors-after.png")
        results["screen"] = {
            "ocr_bad": bad,
            "ocr_tail": text[-400:],
            "palette": info,
            "png": "file-errors-after.png",
        }
        log(f"screen bad={bad} palette={info}")

        passed = sum(1 for c in cases if c.get("ok"))
        results["passed"] = passed
        results["total"] = len(cases)
        results["ok"] = passed == len(cases) and not bad
        rc = 0 if results["ok"] else 1
        log(f"file-error matrix: {passed}/{len(cases)} "
            f"screen_bad={bool(bad)}")
    finally:
        results["finished"] = time.time()
        (OUT / "file-errors.json").write_text(
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
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
