#!/usr/bin/env python3
"""Prove Adam/Hermes/Home.HC and the Load.HC include are inside the ISO.

Boots the release ISO live, then pulls the two files from T: through the
Hermes daemon and compares them with this tree.  No host-side ISO/RedSea
reader is needed and the files are read from the guest's own disc.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from hrpc import Hrpc  # noqa: E402
from qemu_hermes import QMP, start_vm, stop_vm  # noqa: E402

ISO = ROOT / "dist" / "TempleOfHermes-0.1.3.ISO"
OUT = ROOT / "shots" / "hermes-release-0.1.3" / "iso"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def volume_id(path: Path) -> str:
    with path.open("rb") as f:
        f.seek(16 * 2048)
        vd = f.read(2048)
    return vd[40:72].decode("latin-1", "replace").strip()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    meta = start_vm("iso-home-check", ISO, None, memory="2G", boot="d")
    q = QMP(Path(meta["qmp"]), timeout=60)
    h = Hrpc(Path(meta["com1"]), timeout=60,
             log=OUT / "iso-home-check-com1.log")
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        print(f"{name}: {'PASS' if ok else 'FAIL'} {detail}", flush=True)

    try:
        beacon = h.wait_beacon(timeout=180)
        check("beacon", beacon.startswith("HBEACON TempleOfHermes/0.1.3"),
              beacon)
        for key, path, local in (
                ("home", "T:/Adam/Hermes/Home.HC",
                 ROOT / "Adam/Hermes/Home.HC"),
                ("load", "T:/Adam/Hermes/Load.HC",
                 ROOT / "Adam/Hermes/Load.HC"),
                ("version", "T:/Adam/Hermes/VERSION",
                 ROOT / "Adam/Hermes/VERSION")):
            st, data = h.request("pull", path.encode(), timeout=30)
            want = local.read_bytes()
            check(f"iso_{key}", st == "ok" and data == want,
                  f"{len(data)} bytes sha={sha(data)}" if st == "ok"
                  else f"pull {st}")
            if key == "load" and st == "ok":
                check("iso_load_include_home",
                      data.count(b'#include "Home"') == 1,
                      "exactly one #include \"Home\"")
                (OUT / "iso-Load.HC").write_bytes(data)
            if key == "home" and st == "ok":
                check("iso_home_defines_homeinit", b"U8 *HomeInit(" in data,
                      "HomeInit definition present")
                (OUT / "iso-Home.HC").write_bytes(data)
        st, data = h.request("pull", b"T:/Hermes/Apps/Registry.HC", timeout=30)
        check("iso_registry_present", st == "ok" and len(data) > 1000,
              f"{len(data)} bytes" if st == "ok" else st)
        st, data = h.request("ping", b"", timeout=20)
        check("daemon_alive", st == "ok" and b'"pong":1' in data, st)
    finally:
        try:
            h.close()
        except Exception:
            pass
        try:
            stop_vm(meta, q)
        except Exception:
            pass
        try:
            q.close()
        except Exception:
            pass

    result = {
        "iso": str(ISO.relative_to(ROOT)),
        "iso_bytes": ISO.stat().st_size,
        "iso_sha256": sha(ISO.read_bytes()),
        "volume_id": volume_id(ISO),
        "checks": checks,
        "ok": all(c["ok"] for c in checks),
    }
    (OUT / "iso-home-check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"ok": result["ok"],
                      "passed": sum(1 for c in checks if c["ok"]),
                      "total": len(checks)}))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
