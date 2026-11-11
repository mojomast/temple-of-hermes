# ART-VERIFY: Hermes/Art in-OS load check

**Result: PASS.** Wallpaper, icon, and splash all load with `GRRead` returning
non-NULL, blit to the screen, and are captured by QMP. The guest did not crash.

Run date: 2026-11-09/10. Emulator: QEMU 8.2.2, **TCG only**. Guest: public
**TinkerOS 5.20-rc10** live CD.

## What was proven

| Asset | Guest path | `GRRead` | Dimensions | Screenshot |
|---|---|---|---|---|
| Wallpaper | `C:/Hermes/Art/Wallpaper/toh-temple-night.GR` | non-NULL | 640 x 480 | `01-wallpaper-blit.png` |
| Icon | `C:/Hermes/Art/Icons/32/hermes-chat.GR` | non-NULL | 32 x 32 | `02-icon-blit.png` / `02-icon-crop.png` |
| Splash | `C:/Hermes/Art/Splash/toh-boot-splash.GR` | non-NULL | 640 x 480 | `03-splash-blit.png` |

Guest-side marker output (written by the guest after the blits and read back
from the FAT32 overlay):

```text
R_WALLPAPER_OK  GRRead non-NULL ptr=31562278 width=640 winternal=640 height=480
R_ICON_OK       GRRead non-NULL ptr=31562278 width=32  winternal=32  height=32
R_SPLASH_OK     GRRead non-NULL ptr=31562278 width=640 winternal=640 height=480
R_ALL_OK        3/3 assets loaded and blitted
```

All **123** files under `Hermes/Art/` were copied into the guest at
`C:/Hermes/Art/**`. The three required `.GR` files were read back out of the
guest FAT32 image and are byte-identical to the repo copies:

| File | Bytes | SHA-256 |
|---|---:|---|
| `Wallpaper/toh-temple-night.GR` | 307232 | `acd947fa0a0ec8ea488315c06e1037a395cf20fc27e3c4a6482c7b1908779222` |
| `Splash/toh-boot-splash.GR` | 307232 | `6d9f71dfafaeffcff7102f3ea8835547ab1ad4a4ddd2849befb0ceba8c3ed2f3` |
| `Icons/32/hermes-chat.GR` | 1056 | `bdfb6d3c6de4287fac3978c6e6ba3e15c25724b1c70ccbca6ba3d92c84084dc6` |

No image generation was run and the `.GR` assets were not edited.

## Environment

| Item | Value |
|---|---|
| Emulator | QEMU 8.2.2 (`qemu-system-x86_64`, `qemu-img`) |
| Acceleration | `-accel tcg` (no KVM in this sandbox) |
| Machine | `-machine pc,kernel-irqchip=off` |
| CPU / RAM | `-cpu qemu64`, `-smp 1`, `-m 1G` |
| Display / NIC | `-display none`, `-nic none` |
| Video | `-vga std` (640 x 480 VGA) |
| Screenshots | QMP `screendump` -> PNG |
| Guest ISO | `TinkerOS_5.20-rc10.ISO` |
| ISO SHA-256 | `feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4` (verified) |

The in-repo `Extras/TempleOS.ISO` was also used for a preflight run with the
same non-NULL/result; the final captured evidence uses the verified public
TinkerOS 5.20-rc10 ISO named above.

## Procedure

1. Built a 64 MiB MBR + FAT32 overlay image containing the whole
   `Hermes/Art` tree as 8.3 staging files (`F####.BIN`) plus `RUN.HC`.
2. Booted the TinkerOS live CD under QEMU TCG.
3. At the live-CD prompts, answered **no** to install and **no** to the tour.
4. Mounted the overlay as `C:` with `MountIDEAuto;`.
5. Ran `#include "C:/RUN.HC";`. `RUN.HC`:
   - creates `C:/Hermes/Art/{Wallpaper,Splash,Icons/16,Icons/32,Icons/64,Sprites,UI}`,
   - copies every staging file to its long guest path under `C:/Hermes/Art/**`,
   - calls `GRRead` + `GrBlot` for each required asset, with an 8 s settle
     window between blits,
   - writes result markers to `C:/Tmp/R_*`.
6. Captured QMP screenshots continuously during the settle windows, then read
   the marker files and copied assets back from the FAT32 image after the VM
   stopped.

The guest-side blits follow `docs/bees/hermes-art.md` exactly (no extension in
`GRRead`; TempleOS falls back from `.GR.Z` to the uncompressed `.GR`):

```holyC
Cd("C:/Hermes/Art/Wallpaper");
CDC *dc=GRRead("toh-temple-night");
if (dc) { GrBlot(gr.dc,0,0,dc); DCDel(dc); }

Cd("C:/Hermes/Art/Icons/32");
dc=GRRead("hermes-chat");
if (dc) { GrBlot(gr.dc,16,16,dc); DCDel(dc); }

Cd("C:/Hermes/Art/Splash");
dc=GRRead("toh-boot-splash");
if (dc) { GrBlot(gr.dc,0,0,dc); DCDel(dc); }
```

## Screenshot checks

The screenshots are 640 x 480. To score them, each frame pixel is mapped to the
nearest of the 16 standard TempleOS palette entries and compared with the same
mapping of the source `.PNG`. This is necessary because QEMU's VGA DAC is 6-bit,
so raw RGB differs slightly from the 8-bit source values (for example
`170 -> 168`); palette-index equality is the meaningful check.

| Screenshot | Check | Result |
|---|---|---|
| `01-wallpaper-blit.png` | full-frame palette-index match to `toh-temple-night.PNG` | **0.99996** |
| `01-wallpaper-blit.png` | distinct std palette indices / non-black coverage | **16** / **21.5%** |
| `02-icon-blit.png` | 32 x 32 region at (16,16) match to `hermes-chat.PNG` | **1.00000** |
| `02-icon-blit.png` | same region match to wallpaper (control) | 0.85742 |
| `02-icon-blit.png` | full-frame wallpaper match underneath icon | **0.99948** |
| `03-splash-blit.png` | full-frame palette-index match to `toh-boot-splash.PNG` | **0.99987** |
| `03-splash-blit.png` | distinct std palette indices / non-black coverage | **14** / **79.0%** |

The 0.857 control value is expected: the icon is largely dark and the wallpaper
is a night scene, so the wrong image still matches many pixels; the icon frame
is identified by the region matching the icon at **1.00000** while the control
does not.

Wallpaper and splash each cover the full 640 x 480 frame (only the standard
16-colour palette is present; no 24-bit gradients).

## No crash / clean finish

- The guest wrote `R_ALL_OK` (`3/3 assets loaded and blitted`) only after the
  third asset's blit and settle window.
- No exception dialog or allocator panic appeared; the QMP quit was clean.
- The overlay read-back contains all 123 staged files and all marker files.

## Evidence files

```
shots/hermes-art/
  00-overlay-listed.png          # guest Dir("C:/") showing the staging files
  01-wallpaper-blit.png          # GRRead + GrBlot wallpaper
  02-icon-blit.png               # wallpaper + icon at (16,16)
  02-icon-crop.png               # 32x32 icon region, 8x nearest-neighbour
  03-splash-blit.png             # GRRead + GrBlot splash
  evidence.json                  # machine-readable results
  logs/guest-verify.json         # guest marker files + hashes read back
  logs/screenshot-scores.json    # per-screenshot match scores
  logs/run-official.log          # runner log
  logs/run-meta.json             # ISO/guest result metadata
  logs/frame-0050.png            # source frame for the wallpaper shot
  logs/frame-0080.png            # source frame for the icon shot
  logs/frame-0110.png            # source frame for the splash shot
  tools/artqemu.py               # portable QMP/VM helpers
  tools/build_overlay.py         # FAT32 staging image + RUN.HC generator
  tools/run_art.py               # end-to-end boot/stage/blit/screenshot runner
```

## Reproduction

```bash
sudo apt-get update && sudo apt-get install -y qemu-system-x86 qemu-utils
python3 shots/hermes-art/tools/build_overlay.py
python3 shots/hermes-art/tools/run_art.py path/to/TinkerOS_5.20-rc10.ISO run
```

`run_art.py` defaults to `Extras/TempleOS.ISO` when no ISO is given. It writes
its working image and frames under `shots/hermes-art/raw/run*`; the selected
frames are the ones copied to the top-level evidence names above.

## Acceptance checklist

- [x] `GRRead` non-NULL for wallpaper + icon + splash
- [x] screenshots of all three blits
- [x] no guest crash
- [x] only `shots/hermes-art/` and this file changed
- [x] no credentials, network addresses, or private host paths in the evidence
- [x] no image regeneration
- [x] `.GR` assets unchanged (guest copies hash-match the repo)
- [x] no commit, branch switch, merge, tag, or force-push; changes left uncommitted
