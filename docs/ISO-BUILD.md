# Building TempleOfHermes-0.1.2 from the 5.20-rc10 base

This is the same in-guest build path used for 0.1.0 and 0.1.1: install stock
TinkerOS to a qcow2, deliver the Hermes sources with a FAT32 overlay disk, then
let the guest's own `Adam/Hermes/MakeDistro.HC` run `BootDVDIns` / `RedSeaISO`.

No host-side ISO tool is used. `xorriso`, `mkisofs`, and remastering the stock
ISO are explicitly not part of this path.

## Inputs

- Base tree: `hermes/iso-0.1.1` at
  `2ee750e9205809c405aa5494cdfe8d49b35a07d5` (the packed sandbox clone records
  that tree as its single `base` commit; no `origin` remote is present).
- Work branch: `hermes/iso-0.1.2`, created from that packed `HEAD` only.
- Stock CD: `TinkerOS_5.20-rc10.ISO`
  - sha256 `feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4`
  - from the public `tinkeros/TinkerOS` 5.20-rc10 release
  - `scripts/qemu_hermes.py` reads `$TOH_TINKEROS_ISO` or
    `run/TinkerOS_5.20-rc10.ISO`.

## 1. Install to a 4G qcow2

`scripts/build_iso.py` (`install_to_disk`) boots the stock CD with a blank
4G qcow2 (`run/hermes-build.qcow2`) and answers the real installer prompts:

- `Install onto hard drive` -> `y`
- `Perform automated partitioning ...` -> `y`
- `How many would you like to install` -> `1`
- graphics mode -> Enter (640x480)
- extra ISO files -> `n`
- wait for `Reboot Now`, answer `n`, then stop the VM.

Do **not** type the CommInit serial receiver. The overlay never uses the
serial file channel; it uses the FAT32 `D:/RUN.HC` channel.

## 2. FAT32 overlay

`scripts/make_overlay_fat32.py` builds a 64 MiB MBR + FAT32 image with 8.3
names (`RUN.HC`, `F01.BIN`, ...). `build_from_installed.make_run_hc_all` writes
a `RUN.HC` that:

- `DirMk`s every destination directory under `C:/Hermes`, `C:/Adam`, etc.
- `Copy`s each `Fxx.BIN` onto `C:`
- `Del`s the compressed `.Z` twin of every destination
- writes `C:/Tmp/HERMES_OVL_DONE`
- prints `OVERLAY DONE`

The overlay list is `scripts/build_iso.OVERLAY_PATHS` extended by
`build_integration_iso.hermes_overlay()`: every `.HC`, `.DD`, `.GR`, `.TXT`,
and `.PAL` under `Hermes/`. The 0.1.2 build overlays 254 files.

The 0.1.2 launcher and boot changes are:

- `Hermes/Apps/Launcher/`: six-column, three-row borderless full-screen grid
  with all 18 registry entries, a visible selection, per-entry key hints, a
  single ASCII footer help line, mouse hit-testing, arrow/Enter/Space
  navigation, and F1 for About. `RunFile.HC` runs each app in its own visible
  task and restores the launcher when the app exits.
- `Hermes/Apps/Registry.HC`: one unique shortcut per entry and the About run.
- `HomeSys.HC` / `Once.HC` / `StartOS.HC`: one hidden user terminal, the Adam
  boot terminal docked off-screen, and the launcher left as the only visible
  window.
- `Adam/AutoComplete/DoACInit.HC`: the dictionary initializes but the
  AutoComplete / System Keys guide does not open at boot (Alt-A still toggles
  it).
- `Hermes/Apps/Psyche/Run.HC`, `Capybara`, `Codex`, `Dojo`, `WorldSim`, `Net`:
  redraw and return-to-launcher fixes; `Psyche` uses a small text signal-field
  view so the live disc stays responsive.
- `Doc/Start.DD`, `Doc/AboutHermes.DD`, `Once.HC`: 0.1.2 wording.

## 3. In-guest MakeDistro / DoDistro / RedSeaISO

Boot the stock live CD again with:

- installed qcow2 at IDE index 0 (ATA device 1)
- overlay raw image at IDE index **3** (ATA device 3)
- QEMU `-accel tcg -display none -nic none -machine pc,kernel-irqchip=off`

IDE index 2 belongs to the CD-ROM; using it fails with
`drive with bus=1, unit=0 (index=2) exists`.

At the live CD prompts answer `n` to install and `n` to the tour, wait 8 s,
then type slowly (0.14 s/key) at the real HolyC shell:

```
Mount(FALSE,TRUE);      // wizard: C, Enter, s, 1, Enter, Enter
Mount(FALSE,TRUE);      // wizard: D, Enter, s, 3, Enter, Enter
Cd("D:/");
#include "D:/RUN.HC";   // wait for OVERLAY DONE
Cd("C:/");
#include "C:/Adam/Hermes/MakeDistro";   // wait for "ISO written"
```

`MakeDistro.HC` is INT-owned and was not edited.

## 4. Extract

After the guest prints `Temple of Hermes ISO written to ...`, stop the VM,
convert the qcow2 to raw, and use `scripts/fat32_read.extract` on
`/Tmp/TempleOfHermes.ISO.C` (fallbacks `/Tmp/TempleOfHermes.ISO.C.Z` and
`/Tmp/TempleOfHermes.ISO`). The result of this build:

- `dist/TempleOfHermes-0.1.2.ISO`
- size `14030848` bytes
- sha256 `8bcf43c31689e328716ca42f0255f1ede834dd39cd0fa345bc96719d60f74c60`
- ISO9660 volume id `THE_TEMPLE_OF_HERMES`

The ISO is a PC/snapshot artifact. `dist/*.ISO` is gitignored; it is not
committed, released, or deployed.

## 5. Boot the built ISO

```
qemu-system-x86_64 -accel tcg -display none -nic none \
  -machine pc,kernel-irqchip=off -m 2G \
  -cdrom dist/TempleOfHermes-0.1.2.ISO \
  -serial unix:run/com1.sock,server=on,wait=off \
  -serial unix:run/com2.sock,server=on,wait=off
```

COM1 stays the Hermes HRPC console. COM2 is the Hayes-style modem link; the
PIL-only capture uses a local unix-socket stub that answers `ATZ`, `ATD hermes`,
`AT+SEND`, `AT+RECV`, and `ATH` and echoes the guest frame. No BBS, VPS, or
network destination is contacted.

`shots/hermes-iso-0.1.2/capture.py` boots the built ISO with no writable guest
disk, runs 20 independent launcher trials, launches every app by mouse and by
key, and writes the 640x480 16-colour shots. It uses bounded waits and PIL/OCR
only. See `shots/hermes-iso-0.1.2/VERIFY.md` for the 0.1.2 results.
