# Hermes rebrand evidence shots

This directory is for QEMU screendumps and short notes proving the rebrand on a
running image.

## Status

No boot screenshot is committed here. This sandbox has no QEMU installed by
default and no prebuilt `TempleOfHermes-0.1.0.ISO`; the rebrand was verified by
source inspection and text checks instead (see `docs/evidence/rebrand-checks.md`).
The recipe below is the intended capture path once an image is available.

## Capture recipe (TCG, no network)

```bash
qemu-system-x86_64 \
  -accel tcg \
  -machine pc,kernel-irqchip=off \
  -m 2G -smp 1 -vga std \
  -display none -nic none \
  -cdrom <path-to>/TempleOfHermes-0.1.0.ISO \
  -serial unix:/tmp/toh-com1.sock,server=on,wait=off \
  -qmp unix:/tmp/toh-qmp.sock,server=on,wait=off
```

Wait for `HBEACON TempleOfHermes/0.1.0` on the serial socket, then issue a QMP
`screendump` for each checkpoint:

- `01-boot-banner.ppm` — early boot text with `THE TEMPLE OF HERMES 0.1.0`.
- `02-start-page.ppm` — Start page with the product name and version.
- `03-once-welcome.ppm` — the `Once` welcome panel.
- `04-agent-mode.ppm` — presence banner and agent crosshair.
- `05-art-wallpaper.ppm` — a wallpaper/icon blit from `Hermes/Art/`.

Convert to PNG for review if needed. Do not OCR these images for ordinary
reading; use the `text` RPC and keep screenshots for visual evidence only.

## What must be visible

- `THE TEMPLE OF HERMES` in the boot banner, Start page, About page, and Once
  welcome.
- Version `0.1.0` with the `TinkerOS 5.200 base` note.
- The TEMPLE / TinkerOS / TempleOS credit line on the About and Once surfaces.
- The USER / SHARED / AGENT presence banner.

Do not add secrets, tokens, tailnet addresses, or machine-specific home
directory paths to this directory.
