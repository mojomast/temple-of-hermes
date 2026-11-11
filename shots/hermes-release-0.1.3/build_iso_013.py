#!/usr/bin/env python3
"""0.1.3 release ISO wrapper around scripts/build_iso.py.

scripts/build_iso.py describes the 0.1.2 overlay set.  The 0.1.3 integration
merge added Adam/Hermes/Home.HC and Adam/Hermes/FileGuard.HC to the daemon
include chain (Adam/Hermes/Load.HC includes both), plus the two guest test
scripts.  They are source files, not build-script changes, so this wrapper
only extends the module's OVERLAY_PATHS list before running the documented
install -> FAT32 overlay -> MakeDistro -> RedSeaISO path unchanged.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import build_iso  # noqa: E402

EXTRA = [
    "Adam/Hermes/Home.HC",
    "Adam/Hermes/FileGuard.HC",
    "Adam/Hermes/HomeTest.HC",
    "Adam/Hermes/FileErrorsTest.HC",
]

existing = set(build_iso.OVERLAY_PATHS)
for rel in EXTRA:
    if rel not in existing:
        build_iso.OVERLAY_PATHS.append(rel)
        existing.add(rel)

if __name__ == "__main__":
    raise SystemExit(build_iso.main())
