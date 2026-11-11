#!/usr/bin/env python3
"""Text-only OCR scan of every 0.1.2 shot for exception strings."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from qemu_hermes import ocr_variants  # noqa: E402

OUT = ROOT / "shots" / "hermes-iso-0.1.2"
BAD = ("Except:", "ERROR:", "Undefined identifier", "Fault:", "Fatal")


def main() -> int:
    lines, ok = [], True
    files = sorted(OUT.glob("*.png"))
    for p in files:
        texts = ocr_variants(p)
        hits = {b for t in texts for b in BAD if b.lower() in t.lower()}
        if hits:
            lines.append(f"FAIL {p.name} suspicious={sorted(hits)}")
            ok = False
        else:
            best = max(texts, key=lambda t: sum(1 for c in t if c not in " ?"))
            lines.append(f"PASS {p.name} text={best[:100]!r}")
    lines.append(f"RESULT {'PASS' if ok else 'FAIL'} shots={len(files)}")
    (OUT / "OCR-CHECKS.txt").write_text("\n".join(lines) + "\n")
    print(lines[-1])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
