# QEMU sandbox probe for THE TEMPLE OF HERMES

This note records the safe, TCG-only recipe for checking a Hermes image in a
sandbox with no KVM and no network. It is a probe recipe, not a benchmark.

## Limits of this sandbox

- No `/dev/kvm` is assumed. Use `-accel tcg`.
- Networking is off. Use `-nic none`; the guest talks to the host over COM1.
- Use `-machine pc,kernel-irqchip=off` as in the proven TinkerOS plugin flags.
- Do not commit generated ISOs or disk images. `dist/*.ISO` and `*.qcow2` are
  ignored by `.gitignore`.

## Prerequisites

```bash
sudo apt-get update
sudo apt-get install -y qemu-system-x86 qemu-utils
```

Verify the public TinkerOS 5.20-rc10 ISO before using it as a build input:

```text
sha256 feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4
```

## Boot probe

```bash
qemu-system-x86_64 \
  -accel tcg \
  -machine pc,kernel-irqchip=off \
  -m 2G -smp 1 -vga std \
  -display none -nic none \
  -cdrom <hermes-or-tinkeros.iso> \
  -serial unix:/tmp/toh-com1.sock,server=on,wait=off \
  -qmp unix:/tmp/toh-qmp.sock,server=on,wait=off
```

Open the serial socket and wait for one of:

```text
HBEACON TempleOfHermes/0.1.0
```

On a stock TinkerOS ISO there is no beacon; the daemon is part of the Hermes
build. On a Hermes build, a missing beacon means COM1 is not connected, the
daemon did not load, or boot stopped at an earlier error.

## Screenshots

Take QMP screendumps into `shots/hermes-rebrand/` when a visual check is
needed. Keep the frame at the guest's native 640×480; do not upscale a
screenshot for OCR. Prefer the `text` RPC for reading, and use a screenshot
only to confirm the banner, the boot splash, or an art layout.

Suggested captures:

- early boot text (product name and version)
- the Start page / wallpaper banner
- the AGENT-mode presence banner and crosshair
- an art check from `docs/ART.md`

## What to record

For each probe, write a short note under `docs/evidence/` or
`shots/hermes-rebrand/` with:

- the ISO filename and SHA-256 (no local paths)
- QEMU version and the exact acceleration used
- whether `HBEACON` arrived
- the visible banner string
- any error text from the guest or QMP

Do not include secrets, tokens, tailnet addresses, or machine-specific home
directories in evidence files.

## If boot fails

- `!!! Requires 2GB of RAM !!!` — raise `-m`.
- No boot device — check `-cdrom` and the ISO hash.
- Kernel panic before the banner — the image is a stock ISO or a bad rebuild;
  rebuild with `scripts/build_iso.py`.
- Beacon missing but desktop up — check the serial socket and that the build
  includes `Adam/Hermes/Load.HC`.
