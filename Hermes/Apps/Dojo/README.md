# Hermes Dojo (NEW)

A 16-color HolyC practice hall for THE TEMPLE OF HERMES, built for
TinkerOS 5.20-rc10. Load.HC only includes sources; Run.HC creates the
Agent/ folder and launches the hall.

## Run

```holyc
Cd("C:/Hermes/Apps/Dojo");
#include "Run";
```

The hall opens full-screen in the current task and returns to the shell on exit. Keys: `1`-`4` run a scored challenge,
`P` opens the wall plaque, `R` opens the score report, `ESC` exits and
returns to the shell.

## Scored challenges

| # | Challenge | Solution file | Result file |
|---|-----------|---------------|-------------|
| 1 | Draw a caduceus | `Agent/solution1.txt` | `Agent/result1.txt` |
| 2 | Tiny DolDoc form | `Agent/solution2.DD` | `Agent/result2.txt` |
| 3 | 32x32 draw_it sprite | `Agent/solution3.txt` | `Agent/result3.txt` |
| 4 | File echo | `Agent/solution4.txt` | `Agent/result4.txt` |

Challenges 1 and 3 use a tiny drawing language:

```
COLOR n
LINE x1 y1 x2 y2
PLOT x y
RECT x y w h
CIRCLE cx cy r
```

Challenge 2 looks for DolDoc `BT,` / `TX,` tags, a Name field, a Rank
field and a SUBMIT button. Challenge 4 looks for the token
`HERMES-DOJO-ECHO` in a short text file.

Pass is 60+ (challenge 2 needs 75). Every run writes the pass/fail and
score to the result file; nothing is read from the bitmap.

## Agent hook

Write the solution, include the challenge, run it, read the result:

```holyc
Cd("C:/Hermes/Apps/Dojo");
#include "Chal1.HC";
DojoChal1;
Dir("Agent");
```

Or use the CLI wrapper (it writes the same result file):

```holyc
Cd("C:/Hermes/Apps/Dojo");
#include "DojoCli.HC";
DojoCli("1");
```

`DojoCli("1")` through `DojoCli("4")` cover all four challenges. If the hall
is already loaded, call `DojoCli` directly; otherwise include `ChalN.HC`.

## Art and lore

- `header-dojo-plate.GR` is a 640x64 header plate (not a 640x480
  wallpaper), so at most one full-size 640x480 GR is ever resident.
- `teknium-icon.GR` is a 64x64 game-character icon: helmet, shoulders and an
  energy blade. It is not a likeness of any real person.
- Teknium appears only as Kyle's game character. The trainer voice line
  `"Ship first, patch later."` is game dialogue, not a real quote.
- The wall plaque points at
  https://nousresearch.com/nouscoder-14b-a-competitive-olympiad-programming-model
  and `docs/HOLYC-BEST-PRACTICES.md`.

The hall uses only the standard TempleOS 16-color palette.
