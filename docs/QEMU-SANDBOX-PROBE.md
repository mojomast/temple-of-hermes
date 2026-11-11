# QEMU Sandbox Probe

**Question:** can this Cua sandbox install `qemu-system-x86_64` and boot an ISO
under TCG?

**Answer:** yes. QEMU installed from the distro packages, the in-tree
`Extras/TempleOS.ISO` booted with 1 GiB RAM under TCG, a guest framebuffer
screendump was captured, and the VM shut down cleanly. `/dev/kvm` is absent, so
TCG is the only accelerator.

## Environment

| Item | Result |
| --- | --- |
| Host | Linux sandbox, x86_64 |
| Accelerator | TCG (`-accel tcg`), no hardware virtualization |
| `/dev/kvm` | absent (device node does not exist) |
| QEMU | 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.18) |
| `qemu-img` | 8.2.2 |
| Guest RAM | 1 GiB |
| Guest ISO | `Extras/TempleOS.ISO` (in tree, 17,350,656 bytes) |
| ISO SHA-256 | `5d0fc944e5d89c155c0fc17c148646715bc1db6fa5750c0b913772cfec19ba26` |

No ISO download was needed: the repository already ships `Extras/TempleOS.ISO`.
The TinkerOS 5.20-rc10 download and its SHA-256 check were therefore not used
for this probe.

## Install

```sh
sudo apt-get update
sudo apt-get install -y qemu-system-x86 qemu-utils
```

The sandbox has no `/dev/kvm`, so every invocation below uses TCG. KVM was not
attempted.

## Probe command

The probe is self-contained and standard-library only:

```sh
python3 scripts/probe_qemu_sandbox.py
```

It resolves the ISO relative to the repository root, so no host-specific ISO
path is required. Optional flags: `--iso`, `--out`, `--memory`, `--boot`,
`--settle`, `--timeout`, `--json-out`.

Equivalent QEMU invocation used by the script:

```sh
qemu-system-x86_64 \
  -name hermes-qemu-probe \
  -machine pc,kernel-irqchip=off \
  -accel tcg -cpu qemu64 \
  -m 1G -smp 1 -vga std \
  -display none -nic none \
  -qmp unix:shots/hermes-qemu-probe/run/qmp.sock,server=on,wait=off \
  -cdrom Extras/TempleOS.ISO \
  -boot order=d,menu=on -no-reboot
```

After a 25 s settle, the script issues a QMP `screendump` in PNG format, checks
the PNG signature and dimensions, then sends QMP `quit` and waits for the
process to exit (SIGTERM/SIGKILL fallback).

## Results

| Check | Result |
| --- | --- |
| QEMU installed | pass |
| KVM usable | no (`/dev/kvm` absent) |
| TCG boot | pass, guest framebuffer active at 25.1 s |
| Screendump | `shots/hermes-qemu-probe/boot.png` |
| Image | PNG, 640x480, 8-bit RGB, 11,595 bytes |
| Framebuffer content | 10 unique colors, 96.3% non-black sampled pixels |
| VM stopped | pass, QEMU exit code 0, no process left behind |

Machine-readable output is written to `shots/hermes-qemu-probe/probe.json`;
`shots/hermes-qemu-probe/qemu.log` is the (empty) QEMU log.

## Notes and limits

- TCG is slow: the boot screen appears within the 25 s settle window, but
  interactive work would be much slower than on KVM.
- The probe disables networking (`-nic none`) and uses no display window
  (`-display none`); all capture goes through QMP.
- `-machine pc,kernel-irqchip=off` is required for this guest under TCG.
- The script contains no absolute host paths and creates its transient socket
  and PPM files under the output directory, then removes them.
- This probe only boots a prebuilt ISO; it does not rebuild the distro ISO.
