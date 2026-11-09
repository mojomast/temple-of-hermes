# Temple of Hermes Art

Nous-themed visual assets for **THE TEMPLE OF HERMES** (`mojomast/temple-of-hermes`, branch `hermes/art`).

## Theme (no invented facts)

Iconography used here is symbolic / original pixel art only:

- **Hermes the messenger** — caduceus, talaria (winged sandals), temple facade
- **Classical / cyber-occult** — Greek key meander, marble columns, VGA dither, starfield
- **Nous Girl** — original fictional badge character (not a likeness of any real person)
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
