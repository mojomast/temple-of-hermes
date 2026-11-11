# Offerings - Don Piedro's in-guest shop

A small HolyC shop window for wallpapers, palette cards, and local HolyC
snippet packs.  Don Piedro keeps his existing voice: spoons, "Hello I Hermes
biggest fanboi", and "For Hermes!".  The prices are pretend spoons; there is
no real money anywhere in this app.

## Run

```holyc
#include "T:/Hermes/Apps/Offerings/Run.HC";
```

`Load.HC` only defines code.  `Run.HC` includes it and calls `OfferingsRun`,
which spawns the shop in its own task and returns to the shell.  Esc closes
the shop and leaves the shell usable.

## Agent hooks

`OfferingsList` writes the whole catalog plus every source and install path
to `C:/Tmp/Offerings/Results/list.json` (and `last.json`).

`OfferingsGet("wall-nous-girl")` writes one item to
`C:/Tmp/Offerings/Results/get-<id>.json` (and `last.json`).

`OfferingsInstall("snip-drawplate")` installs without opening the window.

The catalog is plain JSON with `currency:"spoons"` and `real_money:false`.
No bitmap OCR is needed; an agent reads the result file.

## Assets

The header is the existing `Hermes/Art/UI/header-offerings-plate.GR`; the
shopkeeper badge is the existing `Hermes/Art/Icons/32/don-piedro.GR`.  The
wallpapers come from `Hermes/Art/Wallpaper/` and include `toh-nous-girl`
(marked NEW).  Nothing here regenerates or redraws the art.  The app keeps at
most one 640x480 `.GR` resident: the selected wallpaper is freed when the
preview closes or another is opened.

Installing copies the chosen `.GR` (or palette/snippet text) into
`C:/Tmp/Offerings/` and then loads that copy with `GRRead`.  No `Adam/` file
is edited and no OS palette is changed; the 16-color TempleOS palette is the
only palette used.

## Files

- `Load.HC` - include-only entry; `Cd(__DIR__);;` first, no windows.
- `Run.HC` - include `Load`, then `OfferingsRun;`.
- `OfferData.HC` - catalog and item lookup.
- `OfferArt.HC` - Hermes path search and art loading.
- `OfferAgent.HC` - result files and installation.
- `OfferDraw.HC` - shop and preview drawing.
- `OfferUI.HC` - spawned task, keys, cleanup.
- `Snippets/` - local HolyC snippet packs (no BBS or Net code).
- `Palettes/` - 16-color palette reference cards.

The BBS HolyC share board is deliberately out of scope; snippet packs stay
local to this directory.
