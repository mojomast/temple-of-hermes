# Spoon - Don Piedro's catch arcade

Don Piedro tosses offerings across the table and the player moves a spoon to
catch them.  The offerings are wallpaper, snippet, and palette tokens plus a
NEW token.  Spoons are pretend; there is no real money in this game.

Don Piedro keeps his existing voice: spoons, "Hello I Hermes biggest fanboi",
and "For Hermes!".

## Run

```holyc
#include "C:/Hermes/Apps/Spoon/Run.HC";
```

`Load.HC` only defines code.  `Run.HC` includes it and calls `SpoonRun`, which
spawns the game in its own window and returns to the shell.  Esc closes the
window and leaves the shell usable.

## Controls

- Left / Right: move the spoon
- Enter or Space: start the round
- Enter after game over: run again
- Esc: quit

## Agent hook

`SpoonAgent(U8 *out_file)` plays a deterministic scripted toss sequence without
opening a window.  It writes `C:/Tmp/SpoonResult.TXT` by default (or the given
path) with caught, missed, score, and toss count.  `Spoon(TRUE)` is the same
hook.

The high score is `C:/Tmp/SpoonScore.TXT`.

## Assets

The game uses the existing art-nous assets:

- `Hermes/Art/UI/header-offerings-plate.GR`
- `Hermes/Art/Icons/{16,32,64}/don-piedro.GR`

No faces are regenerated or redrawn.  At most one 640x480 `.GR` is resident;
the header plate is 640x160 and the shopkeeper badge is loaded at 64x64.  The
16-color TempleOS palette is the only palette used.

## Files

- `Load.HC` - include-only entry; `Cd(__DIR__);;` first, no windows.
- `Run.HC` - includes `Load`, then `SpoonRun;`.
- `SpData.HC` - constants and game state classes.
- `SpArt.HC` - Hermes art lookup, high-score file helpers.
- `SpRand.HC` - deterministic random helpers.
- `SpState.HC` - start, restart, and free.
- `SpToss.HC` - tossing and catch physics.
- `SpRound.HC` - toss scheduling and round end.
- `SpAgent.HC` - deterministic scripted agent play.
- `SpResult.HC` - result file and agent hook.
- `SpDrawTop.HC` - header plate and score bar.
- `SpDrawPlay.HC` - tokens, spoon, and Don Piedro's table.
- `SpDrawOver.HC` - title and round-over overlays.
- `SpDraw.HC` - playfield frame and draw dispatch.
- `SpWindow.HC` - window and menu setup.
- `SpTask.HC` - key loop, timing, and cleanup.
- `SpRun.HC` - spawn entry points and `Spoon(TRUE)`.
