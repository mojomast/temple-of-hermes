# TempleOfHermes-0.1.2-disk.qcow2

`TempleOfHermes-0.1.2-disk.qcow2` is a preinstalled, writable Temple of Hermes
0.1.2 system built from the official v0.1.2 ISO.  It boots with no CD attached
straight to the Hermes Apps launcher and already contains these writable
directories on `C:`:

```
C:/Home
C:/Hermes/Apps/HermesBBS
```

The image uses the same MBR + FAT32 layout that TinkerOS's own installer
creates: one active FAT32 primary partition (type `0x0B`) starting at LBA 63,
a TinkerOS partition boot record, and `Kernel.BIN.C`.  See
`docs/research/preinstalled-disk.md` for the layout and sources.

## Inputs

| Input | Value |
| --- | --- |
| ISO | `TempleOfHermes-0.1.2.ISO` |
| ISO bytes | 14,030,848 |
| ISO SHA-256 | `9afc98ed2bb15a3ff26ebaca12ea392079292df6667b3c1c527fdd30d80cdb13` |
| ISO volume id | `THE_TEMPLE_OF_HERMES` |
| Base tree | `origin/main` at `66a270746d2d157d7060c50d747c8a9f5ba4d50a` |
| Disk virtual size | 4 GiB (4,294,967,296 bytes) |
| Disk file size | 11,082,240 bytes |
| Disk SHA-256 | `d41672fb148051f3b4d85d06895bfc0f67da0e3af539bf89bbf4933056241087` |
| Format | qcow2, zlib-compressed clusters, 64 KiB clusters |

`SHA256SUMS` in the distribution directory lists the image and the ISO.  The
builder itself writes `<output>.SHA256SUMS` next to the image so it does not
overwrite an unrelated checksum file.  It refuses to start if the ISO hash does
not match the value passed on the command line.

## Build

```
python3 scripts/build_disk_image.py \
  --iso TempleOfHermes-0.1.2.ISO \
  --sha256 9afc98ed2bb15a3ff26ebaca12ea392079292df6667b3c1c527fdd30d80cdb13 \
  --iso-size 14030848 \
  --output TempleOfHermes-0.1.2-disk.qcow2
```

The script:

1. verifies the ISO size and SHA-256 (and prints the ISO volume id);
2. creates a blank 4 GiB qcow2;
3. boots the official ISO with QEMU TCG (`-display none -nic none
   -machine pc,kernel-irqchip=off`);
4. closes the live launcher, opens a visible TempleOS terminal, and runs the
   ISO's own `DoInstall(TRUE)` from `Misc/OSInstall.HC`;
5. answers the automated-installer prompts: automated partitioning yes, one
   installation, 640x480 graphics, no extra ISO files, then no to `Reboot Now`;
6. copies the root plain `.HC`/`.DD` files and the `Home` and `Hermes` trees
   (the stock copy step only carries `*.HC.Z` and omits `Hermes`), and creates
   `C:/Home` and `C:/Hermes/Apps/HermesBBS`;
7. verifies the installed FAT32 tree;
8. patches the TinkerOS stage-2 boot menu to select the installed partition
   without a keypress;
9. converts to compressed qcow2, runs `qemu-img check`, and writes
   `<output-stem>.SHA256SUMS`.

Build logs and the intermediate raw image are kept under `run/disk-image/`.
The raw file can be deleted; only the qcow2 and its checksum file are
distributed.

## Verify

```
sha256sum -c SHA256SUMS
qemu-img info TempleOfHermes-0.1.2-disk.qcow2
qemu-img check TempleOfHermes-0.1.2-disk.qcow2
```

`qemu-img info` should report a virtual size of 4 GiB and format `qcow2`;
`qemu-img check` should report no errors.

Run the cold-boot and persistence suite:

```
python3 scripts/test_disk_image.py \
  --image TempleOfHermes-0.1.2-disk.qcow2 \
  --boots 20 --timeout 75
```

The suite boots a fresh VM per trial with no CD, waits up to 75 seconds for the
launcher, requires exactly one visible window titled `Hermes Apps`, writes
dummy marker files through HRPC into the existing `C:` directories, reboots,
and reads them back.  It runs against a copy, so the distributed image is not
modified.  Results and palette-checked screenshots are written under
`shots/hermes-disk-0.1.2/`.

## Boot

```
qemu-system-x86_64 -machine pc,kernel-irqchip=off -accel tcg \
  -cpu qemu64 -m 2G -smp 1 -vga std -display none -nic none \
  -drive file=TempleOfHermes-0.1.2-disk.qcow2,format=qcow2,if=ide,index=0,media=disk \
  -boot order=c,menu=off -serial unix:com1.sock,server=on,wait=off \
  -qmp unix:qmp.sock,server=on,wait=off
```

Do **not** pass `-cdrom`.  The image is self-contained.  COM1 is the Hermes
HRPC console (`HBEACON`/`HREQ`/`HRPL`/`HEVT` at 115200 8n1); `scripts/hrpc.py`
can speak it.

The boot path is TinkerOS's MBR -> stage 2 -> partition boot record ->
`Kernel.BIN.C` -> `C:/Home/Once.HC` -> `Hermes/Apps/Launcher/Run.HC`.  The
stage-2 menu no longer waits for a digit; it selects the installed Drive C
entry automatically.

## Writable C:

The disk is a normal writable qcow2.  Every write the guest makes to `C:` is
stored in the qcow2 and survives shutdown and reboot.  The preinstalled
`C:/Home` and `C:/Hermes/Apps/HermesBBS` directories exist so applications can
write without creating a directory first.

On 0.1.2 the Hermes daemon still has its known missing-directory / read-only-CD
write fault.  Do not push to a path whose directory does not exist and do not
write to the ISO path on this image; create the directory first (or use the
precreated ones above).

## Later 0.1.3 rebuild

The builder is not tied to 0.1.2:

```
python3 scripts/build_disk_image.py \
  --iso TempleOfHermes-0.1.3.ISO \
  --sha256 <0.1.3-sha256> \
  --output TempleOfHermes-0.1.3-disk.qcow2
```

The ISO path, expected hash, output name, and optional expected size are all
CLI inputs.  The installer prompt table at the top of
`scripts/build_disk_image.py` is the only place that would need editing if a
future ISO changes the installer wording.  The resulting `.qcow2` and
`<output-stem>.SHA256SUMS` can be verified with the same commands above.

## BBS token and COM1 on the installed disk

The installed disk is writable, so the normal HermesBBS token location is:

```
C:/Hermes/Apps/HermesBBS/token.txt
```

The app also checks `C:/Hermes/Apps/HermesBBS/token.txt` through the shared
Hermes state directory and then scans every mounted FAT/ISO drive letter (see
[`docs/bbs/TOKEN-PATH.md`](bbs/TOKEN-PATH.md)).  A host can therefore push the
token over COM1, put it on a scratch FAT volume, or write it directly to `C:`
on a copy-on-write overlay; remastering the disk is not required.

The installed disk runs the Hermes daemon on COM1.  `Hermes/Net/Modem.HC`
configures only COM2 and deliberately does not call the global `CommInit()`
once a port is live.  Resetting the whole serial table would clear the
daemon's COM1 state and its next `HEVT` write would fault, which is the old
dead black "Hermes App" window seen when the BBS tile was launched from disk.
`Adam/Hermes/Protocol.HC` also drops a COM1 frame if the host is not reading,
so a disconnected serial client cannot stop the guest.
