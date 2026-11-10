# Dojo Duel (NEW)

A small timed HolyC typing duel for THE TEMPLE OF HERMES on TinkerOS
5.20-rc10. It is separate from the practice hall in `Hermes/Apps/Dojo/`.

## Run

```holyc
Cd("C:/Hermes/Apps/DojoDuel");
#include "Run";
```

The duel opens full-screen and returns to the shell on exit. Type the HolyC
token shown before the 12 second timer expires, then press ENTER. Correct
strikes add a time bonus and grow the streak. The header plate and Teknium
icon are the official `Hermes/Art` assets.

Keys: printable characters type, BACKSPACE fixes, ENTER submits, `P` opens
the wall plaque, ESC leaves.

## Files

- `C:/Tmp/DojoDuelScore.TXT` - best score, best streak and run count.
- `C:/Tmp/DojoDuelResult.TXT` - agent-mode per-challenge PASS/FAIL and total.

## Agent hook

```holyc
Cd("C:/Hermes/Apps/DojoDuel");
#include "Load";
DojoDuel(TRUE);
```

or call `DojoDuelAgent("C:/Tmp/DojoDuelResult.TXT");`. The scripted answers
live in `DuelText.HC`; no bitmap OCR is used.

## Lore

Teknium is Kyle's character from the Nous universe: an energy-blade trainer. Coach lines are
invented game voice marked NEW, not quotes of any real person. The wall
plaque points at
https://nousresearch.com/nouscoder-14b-a-competitive-olympiad-programming-model

Only the standard 16-color TempleOS palette is used.
