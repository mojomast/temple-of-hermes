# Bee plan: Temple of Hermes art in-OS check

Run on **Kyle's PC bees** (DeepSeek Flash / CUA). **Do not** start QEMU on the shared box.

## Goal

Prove `Hermes/Art` assets load inside Temple of Hermes / TinkerOS: wallpaper blits, icons plot, splash shows.

## Inputs

- Branch: `hermes/art` on `mojomast/temple-of-hermes`
- Guest files to copy onto the RedSea/FAT overlay or `::/Hermes/Art/`:
  - `Hermes/Art/Wallpaper/toh-temple-night.GR`
  - `Hermes/Art/Splash/toh-boot-splash.GR`
  - `Hermes/Art/Icons/32/hermes-chat.GR` (and siblings)
  - Optional PNG counterparts if the build has PNG loader demos

## QEMU recipe (bee machine only)

1. Boot the Temple of Hermes ISO (or TinkerOS + overlay) with TCG or KVM as available on the bee host.
2. Copy `Hermes/Art/**` into the guest (floppy overlay, `#include` distro hook, or `CopyTree` from mounted virtio/9p if present).
3. At the HolyC cmd line:

```holyC
Cd("::/Hermes/Art/Wallpaper");
Dir;
CDC *dc = GRRead("toh-temple-night");
if (dc) { GrBlot(gr.dc,0,0,dc); DCDel(dc); }
```

4. Icons:

```holyC
Cd("::/Hermes/Art/Icons/32");
dc = GRRead("hermes-chat");
if (dc) { GrBlot(gr.dc,16,16,dc); DCDel(dc); }
```

5. Splash: same with `::/Hermes/Art/Splash/toh-boot-splash`.

6. Screenshot the VNC/framebuffer after each blit.

## Acceptance

- Wallpaper covers 640×480 with visible temple/caduceus using only std 16 colors (no obvious 24-bit leftover gradients).
- Icon `hermes-chat` is recognizable at 32×32 (caduceus / chat cue).
- `GRRead` returns non-NULL for at least wallpaper + one icon + splash.
- No guest crash / allocator panic during `GRRead`/`GrBlot`.

## Failure hints

- NULL from `GRRead`: wrong extension (try `toh-temple-night.GR` / `.GR.Z`), path, or compressed-only reader mismatch — these files are **uncompressed** (`flags=0`).
- Wrong colors: guest not on `PaletteSetStd`.
- Width skew: `width_internal` must be `(width+7)&~7`; rewriter is `scripts/toh_art_convert.py`.

## Out of scope for bees

- Re-running `GenerateImage`
- Merging `hermes/art` into `hermes/v0`
- Moltussy deploy
