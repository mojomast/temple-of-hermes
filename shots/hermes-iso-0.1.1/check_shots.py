#!/usr/bin/env python3
"""PIL-only checks for the 0.1.1 screenshots.  Never displays an image."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "shots" / "hermes-iso-0.1.1"
EXPECTED = [
    "01-boot-splash.png", "02-home-launcher.png", "03-app-hermes-chat.png",
    "04-app-worldsim.png", "05-app-codex.png", "06-app-psyche.png",
    "07-app-capybara.png", "08-app-messenger.png", "09-app-bbs.png",
    "10-app-threshold.png", "11-app-dojo.png", "12-app-offerings.png",
    "13-app-southpaw.png", "14-app-modem-net.png", "15-game-caduceus.png",
    "16-game-token-rain.png", "17-game-spoon.png", "18-game-dojo-duel.png",
    "19-net-echo.png", "20-shell.png",
]


def main() -> int:
    lines = []
    ok = True
    for name in EXPECTED:
        p = OUT / name
        if not p.is_file():
            lines.append(f"FAIL {name} missing")
            ok = False
            continue
        im = Image.open(p)
        size_ok = im.size == (640, 480)
        mode_ok = im.mode == "P"
        palette = im.getpalette() or []
        used = sorted(set(im.getdata()))
        max_index = used[-1] if used else -1
        off = [i for i in used if i > 15]
        line = (f"{'PASS' if size_ok and mode_ok and not off and max_index <= 15 else 'FAIL'} "
                f"{name} size={im.size[0]}x{im.size[1]} mode={im.mode} "
                f"palette_entries={len(palette)//3} used={len(used)} "
                f"max_index={max_index} off_palette={len(off)}")
        lines.append(line)
        if not (size_ok and mode_ok and not off and max_index <= 15):
            ok = False
    lines.append(f"RESULT {'PASS' if ok else 'FAIL'} shots={len(EXPECTED)}")
    text = "\n".join(lines) + "\n"
    (OUT / "PIL-CHECKS.txt").write_text(text)
    print(text, end="")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
