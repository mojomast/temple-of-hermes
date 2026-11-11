#!/usr/bin/env python3
"""PIL-only checks for every 0.1.3 shot.  Never displays an image."""
from __future__ import annotations

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "shots" / "hermes-daemon-fix-0.1.3"


def main() -> int:
    lines = []
    ok = True
    files = sorted(OUT.glob("*.png"))
    for p in files:
        im = Image.open(p)
        size_ok = im.size == (640, 480)
        mode_ok = im.mode == "P"
        used = sorted(set(im.getdata()))
        max_index = used[-1] if used else -1
        off = [i for i in used if i > 15]
        good = size_ok and mode_ok and not off and max_index <= 15
        lines.append(
            f"{'PASS' if good else 'FAIL'} {p.name} "
            f"size={im.size[0]}x{im.size[1]} mode={im.mode} "
            f"used={len(used)} max_index={max_index} off_palette={len(off)}")
        ok = ok and good
    lines.append(f"RESULT {'PASS' if ok else 'FAIL'} shots={len(files)}")
    text = "\n".join(lines) + "\n"
    (OUT / "PIL-CHECKS.txt").write_text(text)
    print(text, end="")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
