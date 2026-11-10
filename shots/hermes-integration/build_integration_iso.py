#!/usr/bin/env python3
"""Build the integration ISO with the full Hermes tree overlaid.

This is a thin, sandbox-portable wrapper around scripts/build_iso.py.  It
extends the overlay list with the guest-visible files under Hermes/ (HolyC,
DolDoc, GR art, text lore, palettes) so Adam/Hermes/MakeDistro.HC can
CopyTree("/Hermes","/Distro/Hermes") into the disc.

Every QEMU stage remains bounded by the timeouts in scripts/build_iso.py;
run this whole script under an external `timeout` as a second hard cap.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import build_iso  # noqa: E402

KEEP = {".HC", ".DD", ".GR", ".TXT", ".PAL"}


def hermes_overlay() -> list[str]:
    out: list[str] = []
    for path in sorted((ROOT / "Hermes").rglob("*")):
        if path.is_file() and path.suffix.upper() in KEEP:
            out.append(path.relative_to(ROOT).as_posix())
    return out


def main() -> int:
    existing = set(build_iso.OVERLAY_PATHS)
    for rel in hermes_overlay():
        if rel not in existing:
            build_iso.OVERLAY_PATHS.append(rel)
            existing.add(rel)
    return build_iso.main()


if __name__ == "__main__":
    raise SystemExit(main())
