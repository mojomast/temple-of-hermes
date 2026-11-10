# Temple of Hermes Art

Nous-themed visual assets for **THE TEMPLE OF HERMES** (`mojomast/temple-of-hermes`, branch `hermes/art`).

## Theme (no invented facts)

Iconography used here is symbolic / original pixel art only:

- **Hermes the messenger** — caduceus, talaria (winged sandals), temple facade
- **Classical / cyber-occult** — Greek key meander, marble columns, VGA dither, starfield
- **Nous Girl** — fictional game character from AGENT ARMEGEDDON: CLAWPOCALYPSE NOW (not a likeness of any real person and not an official Nous Research mascot). The cine v3 portrait is the default likeness; the earlier generated badge remains in git history of this file's previous revision.
- **Capybara** — pet mascot poses
- **Psyche** — neural-flower / decentralized-training motif (visual metaphor only)
- **WorldSim** — globe with orbiting agent nodes (visual metaphor only)
- **Caduceus** — staff with twin serpents and wings

No real people's likenesses. Lore lines that appear in other branches must stay sourced; this art branch ships pictures and format tooling only.

## TempleOS 16-color palette

Exact `gr32_palette_std` from `Adam/Gr/GrPalette.HC`:

| # | Name | RGB |
|---|------|-----|
| 0 | BLACK | `#000000` |
| 1 | BLUE | `#0000AA` |
| 2 | GREEN | `#00AA00` |
| 3 | CYAN | `#00AAAA` |
| 4 | RED | `#AA0000` |
| 5 | PURPLE | `#AA00AA` |
| 6 | BROWN | `#AA5500` |
| 7 | LTGRAY | `#AAAAAA` |
| 8 | DKGRAY | `#555555` |
| 9 | LTBLUE | `#5555FF` |
| 10 | LTGREEN | `#55FF55` |
| 11 | LTCYAN | `#55FFFF` |
| 12 | LTRED | `#FF5555` |
| 13 | LTPURPLE | `#FF55FF` |
| 14 | YELLOW | `#FFFF55` |
| 15 | WHITE | `#FFFFFF` |

Machine-readable copy: `art/palette.json`.

## Layout

```
art/
  source/          # GenerateImage masters (jpg) + references
  wallpaper/       # 640x480 quantized PNG
  splash/          # 640x480 boot splash PNG
  icons/{64,32,16}/
  sprites/         # sheets
  preview/         # README social 1280x640
  ui/              # pane header strip
  palette.json
Hermes/Art/        # OS-facing assets
  Wallpaper/*.PNG + *.GR + Sprites/*.SP
  Splash/
  Icons/{64,32,16}/  *.PNG *.GR *.SP
  Sprites/
  UI/
scripts/toh_art_convert.py
docs/ART.md
docs/bees/hermes-art.md
```

## App icons (32×32 and 16×16)

`hermes-chat`, `worldsim`, `codex-of-nous`, `psyche`, `capybara-pet`, `messenger-run`, `modem-net`, `home-temple`, plus `nous-girl` badge and six `capy-*` poses.

## Converter

```bash
nice -n 19 python3 scripts/toh_art_convert.py palette
nice -n 19 python3 scripts/toh_art_convert.py wallpaper art/source/FOO.jpg stem
nice -n 19 python3 scripts/toh_art_convert.py splash   art/source/FOO.jpg stem
nice -n 19 python3 scripts/toh_art_convert.py grid     art/source/FOO.jpg ROWS COLS name1 name2 ...
nice -n 19 python3 scripts/toh_art_convert.py sheet    art/source/FOO.jpg stem W H
nice -n 19 python3 scripts/toh_art_convert.py preview  art/source/FOO.jpg stem
nice -n 19 python3 scripts/toh_art_convert.py header   art/source/FOO.jpg pane-header
nice -n 19 python3 scripts/toh_art_convert.py badge    art/source/FOO.jpg nous-girl
```

Pillow only. No QEMU on the box — in-OS checks are for bees (see `docs/bees/hermes-art.md`).

## `.GR` format (uncompressed)

From `Adam/Gr/GrDC.HC` `DCSave` / `KernelA.HH` `CDC` (`start`…`end`):

```
I64  cdt                 # 8
I32  x0, y0              # 8
I32  width               # 4
I32  width_internal      # 4  == (width+7)&~7
I32  height              # 4
I32  flags               # 4  0 = uncompressed, no embedded palette
U8   body[width_internal * height]   # palette indices 0..15
```

Total header 32 bytes. We deliberately omit `DCF_COMPRESSED` (TempleOS `CArcCompress`) so a pure-Python writer stays small; TempleOS `GRRead`/`DCLoad` still loads uncompressed bodies. Optional `DCF_PALETTE` + 16×`CBGR48` is not written — std palette is assumed.

## CSprite / DolDoc `.SP`

Raw element stream starting at `CSprite.start` (no `next`/`last` queue pointers), matching `DC2Sprite` in `Adam/Gr/SpriteNew.HC`:

1. `SPT_BITMAP` (23) element: `U8 type`, 3 pad bytes, `I32 x1,y1,width,height`, then `body[width_internal*height]`
2. `SPT_END` (0)

Embed in DolDoc with `DocSprite` / `$$SP...$$` after loading, or `DocGR` after placing the `.GR` on the guest FS. Vector CSprite ops (lines, flood fills, meshes) are out of scope; bitmaps are enough for wallpaper blit and icons.

## Regeneration note

Masters were generated with the image tool under Kyle's Nov 9–10 unlimited window, then quantized with Floyd–Steinberg (wallpapers/sheets) or nearest-color (tiny icons).


## Cinematic portraits (hermes/art-nous)

Added 9–10 Nov 2026. Kyle approved copying cropped/resized cine v3 portraits from
`mojomast/clawpocalypse-now` (and the already-fitted Hermagotchi copies of the
same stills) into this tree and converting them to the TempleOS 16-color palette.
Backgrounds were generated once each (no faces, no characters) and composited
under the portraits. No photoreal likeness of any real person. In the guest, the
announcer character is named **Southpaw** only — never print "TurboFit".

### Portrait origins

All four masters are the cine v3 stills from `mojomast/clawpocalypse-now` on
the `main` branch, copied into `art/source/cine/`:

| Guest name | In-tree source | Origin path in clawpocalypse-now | Notes |
|---|---|---|---|
| Nous Girl | `art/source/cine/nous_girl.png` | `assets/cine/v3/portraits/nous_girl.png` | Flipped horizontally on the splash, wallpaper, and threshold header so she faces the temple. Also used for the 16/32/64 `nous-girl` badge. |
| Teknium | `art/source/cine/teknium.png` | `assets/cine/v3/portraits/teknium.png` | Game character only, not a likeness of the real person. Dojo header, right side. |
| Don Piedro | `art/source/cine/don_piedro.png` | `assets/cine/v3/portraits/don_piedro.png` | Offerings header, right side. |
| Southpaw | `art/source/cine/southpaw.png` | `assets/cine/v3/portraits/turbofit.png` | Same still Hermagotchi maps as Southpaw (`assets/source/cine_v3_southpaw.png`). The in-tree file is named `southpaw.png`. Stage header, left side. |

Do not copy the multi-megabyte `after/` or `comparison/` rig sheets.

### Generated backgrounds and prompts

Empty architectural plates only, generated once, prompts in
`art/source/generated/PROMPTS.md`:

- `art/source/generated/toh-bg-boot-splash.jpg` — temple threshold, open right third
- `art/source/generated/toh-bg-wallpaper.jpg` — night courtyard, open lower right
- `art/source/generated/toh-bg-header-offerings.jpg` — empty offering hall
- `art/source/generated/toh-bg-header-dojo.jpg` — empty training hall
- `art/source/generated/toh-bg-header-southpaw.jpg` — empty night stage

Title typography on the splash ("THE TEMPLE OF HERMES") was added in the
composite script, not generated.

### Composites and converter outputs

Recompose with `python3 scripts/toh_composite_cine.py`, then:

```bash
nice -n 19 python3 scripts/toh_art_convert.py splash    art/source/composites/toh-boot-splash.png toh-boot-splash
nice -n 19 python3 scripts/toh_art_convert.py wallpaper art/source/composites/toh-nous-girl.png   toh-nous-girl
nice -n 19 python3 scripts/toh_art_convert.py header    art/source/composites/header-threshold.png header-threshold
nice -n 19 python3 scripts/toh_art_convert.py header    art/source/composites/header-dojo.png      header-dojo
nice -n 19 python3 scripts/toh_art_convert.py header    art/source/composites/header-offerings.png header-offerings
nice -n 19 python3 scripts/toh_art_convert.py header    art/source/composites/header-southpaw.png  header-southpaw
nice -n 19 python3 scripts/toh_art_convert.py badge     art/source/cine/nous_girl.png  nous-girl
nice -n 19 python3 scripts/toh_art_convert.py badge     art/source/cine/teknium.png     teknium
nice -n 19 python3 scripts/toh_art_convert.py badge     art/source/cine/don_piedro.png  don-piedro
nice -n 19 python3 scripts/toh_art_convert.py badge     art/source/cine/southpaw.png    southpaw
```

- **Default boot splash** is now the cinematic Nous Girl composite:
  `Hermes/Art/Splash/toh-boot-splash.{PNG,GR}` (replaces the earlier generated
  splash of the same stem; recover the old file from `97d7ad2` if needed).
- **Recommended wallpaper** is `Hermes/Art/Wallpaper/toh-nous-girl.{PNG,GR}` plus
  `Hermes/Art/Sprites/toh-nous-girl.SP`. Earlier wallpapers (`toh-temple-night`,
  `toh-hero`, and the others) are unchanged.
- **Thin UI strips** (1280×80 / 640×40) live under `art/ui/` and
  `Hermes/Art/UI/header-{threshold,dojo,offerings,southpaw}`.
- **In-guest header plates** (640×160) are `Hermes/Art/UI/header-*-plate.{PNG,GR}`
  and matching `.SP` under `Hermes/Art/Sprites/`.

Load one full-screen `.GR` at a time: each 640×480 uncompressed body is ~307 KB.
