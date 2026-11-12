# Disk boot investigation: Temple of Hermes v0.1.3

## Verdict

The official preinstalled disk image is **not** broken when it is booted with
the real `qemu-system-x86_64` and the plugin-equivalent disk argv.  It reaches
the same working Hermes Apps launcher as the official live CD, including the
BBS tile.

The reported black window is caused by the host-side QEMU wrapper on the
affected machine, which appends a second IDE drive at `if=ide,index=0`.
The plugin already puts the Temple of Hermes disk at `index=0`; a duplicate
`index=0` makes QEMU refuse to start (`drive with bus=0, unit=0 (index=0)
exists`).  A display window can appear before that error, which is the dead
black window seen by the user.

No guest or image-build change was required, so no corrected qcow2 was rebuilt
and no release artifact was produced.

## Pinned upstream assets

Downloaded from the official GitHub release `v0.1.3`
(`https://github.com/mojomast/temple-of-hermes/releases/tag/v0.1.3`), then
verified against the release `SHA256SUMS`:

| Asset | Bytes | SHA-256 | Result |
| --- | ---: | --- | --- |
| `TempleOfHermes-0.1.3.ISO` | 14,053,376 | `fbaa3d6f0a8f9190f295e933c32cb833a61b3cb43a708309acb6c98ff51ac4fd` | OK |
| `TempleOfHermes-0.1.3-disk.qcow2` | 11,107,840 | `d81a3c189093bd0edddad50b7a55d6582d0490204d63720e14fc5fb9d901f1aa` | OK |

The disk image was kept read-only; the disk boot used a copy-on-write qcow2
overlay whose backing file is the verified official image.

Base tree: `origin/main` / tag `v0.1.3` at
`c5be4b9730bd4f9e40446f728defd61d46ab2c84`.
Work branch: `hermes/disk-boot-fix`.  Nothing was committed.

## Environment

Host QEMU: `qemu-system-x86_64` 8.2.2 (Ubuntu package), TCG only.
All runs used `-machine pc,kernel-irqchip=off -accel tcg -cpu qemu64
-m 2G -smp 1 -vga std -display none -nic none` and were bounded by a timeout.
QMP was used only for `screendump` and shutdown.  No guest was left running.

## Exact argv

Working directory: a release-asset directory containing the two verified
files.  Paths below are relative; no host user paths are recorded.

Live CD (official ISO; scratch disk at IDE index 1; no hard-disk index 0):

```
qemu-system-x86_64 -name toh-cd \
  -machine pc,kernel-irqchip=off -accel tcg -cpu qemu64 \
  -m 2G -smp 1 -vga std -display none -nic none \
  -cdrom TempleOfHermes-0.1.3.ISO \
  -drive file=scratch-cd.qcow2,format=qcow2,if=ide,index=1,media=disk \
  -boot order=d,menu=off \
  -qmp unix:qmp.sock,server=on,wait=off
```

Official disk (plugin-equivalent, no CD, no extra drive):

```
qemu-img create -f qcow2 -b TempleOfHermes-0.1.3-disk.qcow2 \
  -F qcow2 disk-overlay.qcow2
qemu-system-x86_64 -name toh-disk \
  -machine pc,kernel-irqchip=off -accel tcg -cpu qemu64 \
  -m 2G -smp 1 -vga std -display none -nic none \
  -drive file=disk-overlay.qcow2,format=qcow2,if=ide,index=0,media=disk \
  -boot order=c,menu=on \
  -qmp unix:qmp.sock,server=on,wait=off
```

Collision trial (one bounded run, throwaway blank disk, no user image):

```
qemu-img create -f qcow2 dummy-index0.qcow2 64M
timeout 45 qemu-system-x86_64 -name toh-collision \
  -machine pc,kernel-irqchip=off -accel tcg -cpu qemu64 \
  -m 2G -smp 1 -vga std -display none -nic none \
  -drive file=TempleOfHermes-0.1.3-disk.qcow2,format=qcow2,if=ide,index=0,media=disk,readonly=on \
  -drive file=dummy-index0.qcow2,format=qcow2,if=ide,index=0,media=disk \
  -boot order=c,menu=on
```

Collision result:

```
qemu-system-x86_64: -drive file=dummy-index0.qcow2,format=qcow2,if=ide,index=0,media=disk: drive with bus=0, unit=0 (index=0) exists
exit=1
```

This is the wrapper failure mode.  The wrapper contributes a second
`if=ide,index=0` drive; the plugin's disk is already at `index=0`, so the VM
never boots.  The same machine boots the live CD because the live argv puts
its scratch disk at `index=1` and boots from `-cdrom`.

## Boot observations

Launcher presence was confirmed programmatically from the screendump pixels
with the repository's existing `glyph_text` helper (no PNG was opened or
viewed in-model).  Detected text in both runs included:

```
THE TEMPLE OF HERMES  v0.1.3
18 apps and games
Click an icon or press its key to open - Esc returns here - F1 help
```

The `BBS` launcher tile text was present in both the CD and the official-disk
frames.

## Screenshots (PIL checks only)

Both images are palette PNGs converted from the QEMU 640x480 RGB screendump.
They use the standard 16-color VGA palette (`0/85/170/255` components) and
contain only indices 0-15.  Off-palette source pixels were remapped to the
nearest VGA color and counted; the count is zero.

| File | Bytes | Size | Mode | Unique colors | Max index | Off-palette pixels |
| --- | ---: | --- | --- | ---: | ---: | ---: |
| `01-cd-launcher.png` | 7,394 | 640x480 | P | 15 | 15 | 0 |
| `02-disk-official.png` | 7,393 | 640x480 | P | 15 | 15 | 0 |

Screenshot SHA-256:

```
93196a7c16ae18f934746ec5a48e4b8e2ec581ed7b7df96f9f07bec6af9b952a  01-cd-launcher.png
da6c29212967bea7bd89bedbdccda918ee5fec01e79d153d3a2dd57d0bb4c5a9  02-disk-official.png
```

- `01-cd-launcher.png`: official ISO boot, launcher and full tile grid visible.
- `02-disk-official.png`: official qcow2 boot through a COW overlay, same
  launcher and full tile grid visible, including the BBS tile.

## Guest path audit

The black-window report suggested a guest dependency on the CD.  The audited
boot path does not have one:

- `Once.HC` -> `HermesStartApps` tries `::/Hermes/Apps/Launcher/Run.HC`, then
  `T:/...`, then `C:/...`, then `~/...`.  On a hard-disk boot the current/boot
  drive resolves to C:, which is where the installed launcher lives.
- The installed `C:/Hermes` tree contains the launcher, app registry, icons,
  and `Hermes/Apps/HermesBBS`, so the BBS tile loads without T:.
- The launcher draws its full grid from `C:/Hermes/Art/Icons/32`, which is
  present on the official disk.

The empirical result matches the audit: the official disk reaches the same
launcher and BBS tile as the CD with no CD attached.

## Conclusion

Root cause: host-side wrapper / duplicate IDE `index=0`, not the guest image.
The coordinator's plugin change to skip the PATH wrapper and use the real
`qemu-system-x86_64` is the correct fix.  No guest source, boot script, or
disk-image build was changed, and no image was rebuilt or published.
