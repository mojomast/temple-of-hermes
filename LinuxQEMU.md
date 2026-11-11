# Running THE TEMPLE OF HERMES on Linux with QEMU

THE TEMPLE OF HERMES is a TempleOS-family system based on TinkerOS 5.20-rc10.
It uses the same QEMU device model as TinkerOS: a PC machine with legacy boot,
PS/2 input (or VMMouse), and an IDE CD-ROM. Networking is optional and is off
for the agent image.

The original upstream TinkerOS/TempleOS guide is preserved at
[`docs/upstream/LinuxQEMU.md`](docs/upstream/LinuxQEMU.md).

## Setup

1. Enable virtualization in the BIOS if you have it.
2. Enable KVM if your CPU and host support it. In a sandbox without
   `/dev/kvm`, use `-accel tcg`; it is slower but works.
3. Install 64-bit QEMU from your package manager.
4. Get a bootable image:
   - THE TEMPLE OF HERMES: build `TempleOfHermes-0.1.2.ISO` with
     `scripts/build_iso.py`, or use a verified release image.
   - Stock TinkerOS: <https://github.com/tinkeros/TinkerOS/releases>
   - TempleOS: <http://templeos.org/Downloads/TOS_Distro.ISO>

## Test run from CD

### THE TEMPLE OF HERMES (TCG, no network, serial on a socket)

```bash
qemu-system-x86_64 \
  -m 2G \
  -accel tcg \
  -machine pc,kernel-irqchip=off \
  -smp 1 -vga std \
  -display sdl -nic none \
  -cdrom TempleOfHermes-0.1.2.ISO \
  -serial unix:/tmp/toh-com1.sock,server=on,wait=off
```

With KVM available, replace `-accel tcg` with `-accel kvm,kernel-irqchip=off`.
For a headless probe, use `-display none` and QMP screendumps; see
[`docs/QEMU-SANDBOX-PROBE.md`](docs/QEMU-SANDBOX-PROBE.md).

### Upstream TinkerOS / TempleOS

```bash
qemu-system-x86_64 -m 2G -accel kvm,kernel-irqchip=off -smp 4 \
  -audiodev sdl,id=snd0 -machine pc,pcspk-audiodev=snd0 \
  -display sdl -cdrom TOS_Distro.ISO

qemu-system-x86_64 -m 2G -accel kvm,kernel-irqchip=off -smp 4 \
  -audiodev sdl,id=snd0 -machine pc -device adlib,audiodev=snd0 \
  -display sdl -cdrom TinkerOS_5.14.ISO
```

## Install to a virtual hard drive

```bash
qemu-img create toh.qcow2 512M
qemu-system-x86_64 -m 2G -accel tcg -machine pc,kernel-irqchip=off \
  -smp 1 -display sdl -nic none \
  -cdrom TempleOfHermes-0.1.2.ISO -hda toh.qcow2
```

On the Hermes image, the live CD does not start the installer automatically.
Run `OSInstall` from USER mode when you want to install. In AGENT mode the
input gate refuses install and format operations by design.

## Notes

- QEMU's PC-speaker emulation is rough. TinkerOS's Adlib/OPL path sounds better
  where it is available.
- Without KVM the guest is slow; the agent should prefer the serial `text` and
  `idle` operations over screenshot polling.
- The Hermes image expects COM1 for the guest daemon. Attach a socket or PTY and
  wait for the `HBEACON` line (the daemon string may still read
  `HBEACON TempleOfHermes/0.1.0` on this 0.1.2 build) before sending requests.
- Networking stays off for the agent image. See
  [`docs/HERMES-FEATURES.md`](docs/HERMES-FEATURES.md) for the serial protocol.
