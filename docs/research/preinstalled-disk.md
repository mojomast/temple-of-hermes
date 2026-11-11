# Preinstalled Temple of Hermes disk images

This note records the reasoning behind `TempleOfHermes-0.1.2-disk.qcow2`, a
redistributable preinstalled disk built from the official
`TempleOfHermes-0.1.2.ISO`.  It covers the image format, the MBR + FAT32 layout
that TinkerOS itself creates, the installer automation that already existed in
this repository, compression, and why files on `C:` survive with the CD
removed.  Sources are listed at the end.

## 1. qcow2 versus raw

`raw` is a flat, sector-for-sector image.  It is the simplest interchange
format and can be written with `dd`, but a 4 GiB virtual disk is normally
redistributed as a 4 GiB file unless the host filesystem supports sparse files.
Sparse holes are a property of the host filesystem, not of the image, so they
do not reliably survive archives, uploads, or copies between filesystems.  Raw
also has no room for QEMU metadata such as snapshots or backing files.

`qcow2` is QEMU's copy-on-write block format.  It allocates host space for used
clusters only, keeps refcount and L1/L2 metadata, and can store clusters
compressed.  `qemu-img` can create, inspect, check, and convert it, and QEMU can
use it directly as a writable disk.  That combination is why qcow2 is the usual
redistributable form for QEMU guests: one self-describing file, much smaller
than the virtual size, and writable after download.

The build therefore starts with a blank 4 GiB `qcow2`, installs into it, and
ships a compressed `qcow2`.  A raw image can always be produced later with
`qemu-img convert -O raw` when a tool needs a flat disk.  The artifact is not
raw because a flat 4 GiB file would be dominated by zeroes and because
compressed qcow2 is both smaller and directly bootable.

Relevant QEMU behaviour:

- qcow2 supports sparse allocation, snapshots, backing files, and compressed
  clusters ([QEMU images documentation](https://www.qemu.org/docs/master/system/images.html)).
- `qemu-img convert` changes formats; `-c` requests compression and
  `-O qcow2` selects the output format
  ([qemu-img documentation](https://www.qemu.org/docs/master/tools/qemu-img.html)).
- `qemu-img check` validates metadata and reports allocated/compressed cluster
  counts.
- QEMU's QMP monitor is the control channel used for screendumps and key
  injection ([QMP specification](https://www.qemu.org/docs/master/interop/qmp-spec.html)).

## 2. The MBR + FAT32 layout TinkerOS actually installs

The installer is not a generic Linux installer and the disk is not ext4, GPT,
or a container format.  TinkerOS's own partitioner and formatter create the
layout:

- `Misc/OSInstall.HC` (`DoInstall`, `VMInstall`, `InstallDrv`) drives the
  install.  In automated mode it calls `DskPrt(,1.0)` for one installation,
  then `Fmt` on the new partition, copies the release tree with `Copy` /
  `CopyTree`, and calls `BootHDIns`.
- `Adam/ABlkDev/DskPrt.HC` writes a 512-byte master boot record: boot code in
  the first 446 bytes, four 16-byte partition entries at offset `0x1BE`, and
  the `0xAA55` signature.  Partition starts are `DRV_HEADER` (63) blocks past
  the start of the disk.  The entry is marked active (`0x80`) and given the
  FAT32 type by `Fmt`.
- `Adam/Opt/Boot/BootHDIns.HC` compiles the compiler and kernel on the target
  drive, moves `Kernel.BIN.Z` to `Kernel.BIN.C`, and writes the partition boot
  record so the partition can load that kernel.
- `Adam/Opt/Boot/BootMHDIns.HC` installs the master boot loader, saves the
  previous MBR as `0000Boot/OldMBR.BIN.C`, and writes the stage-2 menu
  (`0000Boot/BootMHD2.BIN.C`).  `Adam/Opt/Boot/BootMHD2.HC` shows that menu
  reads one digit and then loads the selected partition's first sector.
- `Doc/Install.DD` documents the same manual sequence: `DskPrt('C')`,
  `Fmt(...,FSt_FAT32)`, `CopyTree`, `BootHDIns`, `BootMHDIns`.

The shipped image follows that layout exactly: one active FAT32 (type `0x0B`)
primary partition starting at LBA 63, with the TinkerOS partition boot record
and `Kernel.BIN.C` written by `BootHDIns`.  No foreign partition scheme was
introduced.  `compiled evidence`: the image's MBR has signature `0xAA55`, one
entry with boot flag `0x80`, type `0x0B`, start LBA 63, and 8,385,867 sectors,
and the FAT32 root contains `Kernel.BIN.C` (265,616 bytes), `StartOS.HC`,
`Home/Once.HC`, `Home/HomeSys.HC`, and `Hermes/Apps/Launcher/Run.HC`.

The one boot-path adjustment is deliberate and small: the TinkerOS stage-2
menu always prints `Selection:` and waits for a digit, even when there is only
one installed partition.  A preinstalled image must boot unattended, so the
build replaces the menu's single-key read with `AL='1'` in
`0000Boot/BootMHD2.BIN.C`; entry 1 is the installed Drive C entry (entry 0 is
the saved old MBR).  The MBR code and partition table, the FAT32 filesystem,
the partition boot record, and `Kernel.BIN.C` are untouched.  The boot still
goes through TinkerOS's own MBR -> stage 2 -> partition boot record -> kernel
path; only the menu's keypress is removed.  If the old-MBR entry is absent the
build refuses to patch rather than guessing an entry number.

## 3. Installer automation already in this repository

`docs/ISO-BUILD.md` documents the stock automation and
`scripts/build_iso.py` (`install_to_disk`) implements it with QMP keystrokes
and bounded OCR waits:

1. boot the install CD with a blank 4 GiB qcow2;
2. wait for `Install onto hard drive`, answer `y`;
3. wait for `automated partitioning`, answer `y`;
4. wait for `How many would you like to install`, answer `1`;
5. wait for `Select graphics mode for drive C:`, press Enter for 640x480;
6. wait for `extra supplemental ISO files`, answer `n`;
7. wait for `Reboot Now`, answer `n`, and stop the VM.

That helper installs **stock TinkerOS**.  The official Temple of Hermes ISO is
different: its `Once.HC` deliberately skips the live-CD install and tour
prompts and starts the Hermes launcher immediately, so the boot prompt sequence
above never appears.  The installer code is still on the ISO, so the new
builder boots the official ISO, closes the live launcher, opens a visible
TempleOS terminal, and runs the ISO's own `DoInstall(TRUE)`:

- `#define __CMD_LINE__ 0` is set before `#include "T:/Misc/OSInstall.HC"` so
  the include does not auto-run `OSInstall`; the terminal then calls
  `DoInstall(TRUE)` explicitly.
- The same prompt sequence is answered with real QMP keystrokes.  `YorN`
  consumes one character, so yes/no answers are sent without a trailing
  newline; numeric prompts are sent with a newline.

Three properties of this particular ISO had to be handled, and all are
host-side build logic, not guest source changes:

1. **Daemon activity during the install.**  The 0.1.2 Hermes daemon emits
   `HEVT` events on COM1.  Its serial write path (`HermesSendRaw` ->
   `CommPutBlk` -> `CommPutChar`) throws `ComErr` if the installer's IRQ/port
   probing interrupts a write in progress, and the unhandled exception drops
   the guest into the TinkerOS debugger.  The builder stops the daemon for the
   duration of the install, which makes the guest equivalent to the stock
   installer that the existing helper drives.  Guest HolyC is not modified.
2. **Uncompressed root files.**  The ISO root stores `StartOS.HC`, `Once.HC`,
   `HomeSys.HC`, and `MakeHome.HC` as plain `.HC`, while the stock
   `InstallDrv` copies only `*.HC.Z` and the standard trees (`Adam`, `Apps`,
   `Doc`, `Demo`, `Downloads`, `Compiler`, `Kernel`, `Misc`).  It also does not
   copy the Hermes tree.  A disk built by the raw installer therefore boots to
   `File not found: "C:/StartOS.HC.Z"`.  The builder copies `T:/*.HC` and
   `T:/*.DD`, then `T:/Home` and `T:/Hermes`, and creates `C:/Home` and
   `C:/Hermes/Apps/HermesBBS` before sealing the image.
3. **Unattended boot.**  The stage-2 menu keypress described above is removed
   in the finished image.

The shell and QMP plumbing reuse the patterns in `scripts/qemu_hermes.py`
(QMP screendump, `send-key`, `type_text`) and `scripts/hrpc.py`
(`HBEACON`/`HREQ`/`HRPL`/`HEVT` over COM1).  `scripts/build_iso.py` itself is
not modified; the new builder is `scripts/build_disk_image.py`.

## 4. Compression and image size

The builder installs into a 4 GiB qcow2 (the documented stock size), copies
the missing files, verifies the FAT32 contents, and converts the working image
to a compressed qcow2:

```
qemu-img convert -f raw -O qcow2 -c -o cluster_size=65536 installed.raw output.qcow2
qemu-img check output.qcow2
```

Recorded result for 0.1.2:

- virtual size: 4 GiB (4,294,967,296 bytes)
- actual file size: 11,082,240 bytes (10.57 MiB)
- clusters: 300 of 65,536 allocated, 84.67% of allocated clusters compressed
- `qemu-img check`: no errors
- SHA-256 and the exact byte count are in
  `shots/hermes-disk-0.1.2/VERIFY.md`.

Compressed qcow2 clusters are decompressed on demand.  A cluster that the
guest writes is rewritten uncompressed, so the image remains writable; the
compression is a distribution optimisation, not a read-only snapshot.

## 5. Why files on `C:` persist without the CD

The installation copies the release tree onto the FAT32 partition inside the
qcow2.  `BootHDIns` writes the partition boot record and `Kernel.BIN.C` to that
same partition, and `BootMHDIns` writes the MBR and stage-2 loader.  On a cold
boot with no CD attached:

1. the MBR loads the stage-2 loader;
2. the stage-2 loader loads the partition boot record;
3. the partition boot record reads `Kernel.BIN.C` from the FAT32 partition;
4. the kernel mounts that partition as `C:` and uses `C:/Home` as the home
   directory.

All guest writes after that (HRPC `push`, application state, `Once` state,
`/Tmp`) go to the same FAT32 volume, whose sectors live in the qcow2 file.  The
CD is only an install-time source and is never opened by the boot path.  The
verification suite proves this with marker files written under `C:/Home` and
`C:/Hermes/Apps/HermesBBS`, a cold reboot with no CD, and a byte-for-byte read
back through HRPC.

## 6. Re-running for a later ISO

The builder takes the ISO path and expected SHA-256 as required inputs and the
output path as an argument, for example:

```
python3 scripts/build_disk_image.py \
  --iso TempleOfHermes-0.1.3.ISO \
  --sha256 <expected-sha256> \
  --output TempleOfHermes-0.1.3-disk.qcow2
```

No installer prompt text, partition arithmetic, or paths to the 0.1.2 artifact
are hard-coded in the tool beyond the shared TempleOS layout.  If a future ISO
changes the installer wording, the prompt table at the top of the script is the
single place to update.

## Sources

- QEMU, *System emulation: Disk images*:
  https://www.qemu.org/docs/master/system/images.html
- QEMU, *qemu-img*: https://www.qemu.org/docs/master/tools/qemu-img.html
- QEMU, *QMP specification*:
  https://www.qemu.org/docs/master/interop/qmp-spec.html
- Microsoft, *Microsoft EFI FAT32 File System Specification*:
  https://learn.microsoft.com/en-us/windows/win32/fileio/microsoft-efi-fat32-file-system-specification
- *Master boot record* (partition table layout and signature):
  https://en.wikipedia.org/wiki/Master_boot_record
- TempleOS: https://templeos.org/
- TinkerOS: https://github.com/tinkeros/TinkerOS
- Temple of Hermes v0.1.2 release:
  https://github.com/mojomast/temple-of-hermes/releases/tag/v0.1.2
- This repository:
  - `docs/ISO-BUILD.md` (stock install prompt sequence and in-guest ISO build)
  - `scripts/build_iso.py` (`install_to_disk`)
  - `scripts/qemu_hermes.py` (QMP, COM1, OCR helpers)
  - `scripts/hrpc.py` (HBEACON/HREQ/HRPL/HEVT client)
  - `Misc/OSInstall.HC` (`DoInstall`, `VMInstall`, `InstallDrv`)
  - `Adam/ABlkDev/DskPrt.HC` (MBR writer)
  - `Adam/Opt/Boot/BootHDIns.HC` (partition boot record and kernel)
  - `Adam/Opt/Boot/BootMHDIns.HC` (master boot loader and stage 2)
  - `Adam/Opt/Boot/BootMHD2.HC` (stage-2 menu code)
  - `Doc/Install.DD` (manual install sequence)
