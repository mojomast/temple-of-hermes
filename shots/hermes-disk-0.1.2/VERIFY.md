# TempleOfHermes-0.1.2-disk.qcow2 verification

## Inputs

| Item | Value |
| --- | --- |
| ISO | `TempleOfHermes-0.1.2.ISO` |
| ISO bytes | 14,030,848 |
| ISO SHA-256 | `9afc98ed2bb15a3ff26ebaca12ea392079292df6667b3c1c527fdd30d80cdb13` |
| ISO volume id | `THE_TEMPLE_OF_HERMES` |
| Base tree | `origin/main` at `66a270746d2d157d7060c50d747c8a9f5ba4d50a` |
| Work branch | `hermes/disk-image-0.1.3`, created with `git checkout -B hermes/disk-image-0.1.3 HEAD` |

The ISO hash was recomputed in the sandbox before use and matched exactly.
The builder refuses a mismatched or oversized ISO.

## Artifact

| Item | Value |
| --- | --- |
| File | `TempleOfHermes-0.1.2-disk.qcow2` |
| Format | qcow2, zlib-compressed clusters, 64 KiB clusters |
| Virtual size | 4 GiB (4,294,967,296 bytes) |
| Actual file size | 11,082,240 bytes (10.57 MiB) |
| SHA-256 | `d41672fb148051f3b4d85d06895bfc0f67da0e3af539bf89bbf4933056241087` |
| `qemu-img check` | no errors; 300/65,536 clusters allocated, 84.67% compressed |
| Partition layout | MBR, one active FAT32 (type `0x0B`) partition at LBA 63, 8,385,867 sectors |
| `Kernel.BIN.C` | 265,616 bytes on `C:` |

`SHA256SUMS` (repository root of the deliverable, next to the image) lists the
image and the ISO.

## Build method and the three required adaptations

Built by `scripts/build_disk_image.py`.  The script boots the official ISO,
opens a visible TempleOS terminal, runs the ISO's own
`Misc/OSInstall.HC -> DoInstall(TRUE)`, and answers the real installer prompts:
automated partitioning `y`, one installation `1`, graphics `0` (640x480),
extra ISO files `n`, `PressAKey`, then `Reboot Now` `n`.  The stock helper in
`scripts/build_iso.py` is unchanged and was used as the reference for the QMP
prompt handling.

Adaptations, all host-side:

1. **Daemon stopped for the install.**  The 0.1.2 Hermes daemon emits `HEVT`
   events on COM1; its `CommPutChar` path faults (`ComErr`) if the installer's
   IRQ/port probing interrupts a write, and the guest drops to the TinkerOS
   debugger.  The builder stops the daemon for the install, which matches the
   stock installer environment.  Guest HolyC is not modified.
2. **Missing plain root files and Hermes tree.**  This ISO stores
   `StartOS.HC`, `Once.HC`, `HomeSys.HC`, and `MakeHome.HC` uncompressed, while
   `InstallDrv` copies only `*.HC.Z` and omits `Hermes`.  A raw stock copy
   boots to `File not found: "C:/StartOS.HC.Z"`.  The builder copies
   `T:/*.HC`, `T:/*.DD`, `T:/Home`, and `T:/Hermes`, then creates
   `C:/Home` and `C:/Hermes/Apps/HermesBBS`.
3. **Unattended boot.**  The TinkerOS stage-2 menu always waits for a digit.
   The builder replaces that single-key read in
   `0000Boot/BootMHD2.BIN.C` with `AL='1'`, which selects the installed Drive C
   entry (entry 0 is the saved old MBR).  The MBR, partition table, FAT32
   filesystem, partition boot record, and `Kernel.BIN.C` are untouched.  The
   build refuses to patch if the old-MBR entry is absent.

## Cold boot log (no CD attached)

Captured from a cold boot of the sealed image with no `-cdrom` and no other
disk.  QEMU: TCG, `-display none -nic none -machine pc,kernel-irqchip=off`,
`-boot order=c,menu=off`, `-serial unix:...,server=on,wait=off`,
`-qmp unix:...,server=on,wait=off`.  The stage-2 menu auto-selected entry 1;
no key was sent.

```
TinkerOS V5.200 11/11/26 21:35:48

Enable IRQ's
DskChg(':');

Defined Drives:
B REDSEA   RAM        0000 0000 00
   0000000000000058-0000000000020000
C FAT32    ATA        01F0 03F4 00
   Model# :QEMU HARDDISK
   Serial#:QM00001
   000000000000003F-00000000007FF589
T ISO9660  ATAPI      0170 0374 00
   0000000000000000-FFFFFFFFFFFFFFFF
Home Dir:"C:/Home"
MultiCore Start

Loading Compiler
```

The launcher follows; `launcher-ocr.txt` is the OCR of the 640x480 launcher
frame from that boot.  The kernel's drive report lists an ATAPI slot with an
all-ones range; the QEMU command contained no CD device, no CD was read, and
the boot proceeded from `C:` alone.

## A. Cold boots with no CD: 20/20

Twenty independent VMs, each a new process against a copy of the sealed
image, no CD, and a 75 s bound:

- **20/20 passes.**
- Launcher time: min 6.9 s, median 9.0 s, max 9.2 s.
- A pass required OCR to show the launcher (`Hermes Apps` / `Click an icon`)
  **and** the HRPC `windows` list to contain exactly one visible window,
  titled `Hermes Apps`.  Any `Install onto hard drive`, `Take Tour`,
  `System Keys Quick Guide`, `AutoComplete is in StandBy`, or debugger text
  failed the trial.
- Trial data: `boot-trials.json`; text log: `boot-trials.log`.
- Screenshots: `boot-01.png` through `boot-20.png`, each 640x480, mode `P`,
  15 palette indices (0-15), 0 off-palette pixels, verified with PIL.

The trials ran against a copy of the sealed image.  The source image hash was
recorded before and after (`summary.json`) and was unchanged:
`d41672fb148051f3b4d85d06895bfc0f67da0e3af539bf89bbf4933056241087`.

## B. Persistence across a cold reboot

Run on a copy of the sealed image (`persistence.json`):

1. Boot with no CD; before any write, HRPC `list` confirmed the precreated
   directories `C:/Home` and `C:/Hermes/Apps/HermesBBS` exist.
2. Push two dummy marker files through HRPC into those directories:
   - `C:/Home/TEST-MARKER.TXT` — 12 bytes, pull back identical.
   - `C:/Hermes/Apps/HermesBBS/TEST-TOKEN.TXT` — 11 bytes, pull back
     identical.  It is an obvious dummy token-shaped marker; its value is not
     printed.
3. Follow-up `ping` on the same connection: `ok`.
4. Cold reboot with no CD; the launcher returned and HRPC `pull` returned both
   files with identical byte counts and contents.
5. Follow-up `ping` after the reboot: `ok`.

Result: **both marker files persisted and matched**.  `persistence-launcher.png`
is the post-reboot launcher frame (640x480, mode `P`, max palette index 15,
0 off-palette pixels).

## C. Daemon writes to existing `C:` directories through HRPC

The `push` + `pull` pairs above are the daemon write test: the daemon wrote
both files to the FAT32 `C:` partition and read the same bytes back, and a
subsequent `ping` succeeded.  No missing directory and no CD/ISO path was used
for a write.

## D. 0.1.2 crash path avoided

The 0.1.2 daemon still faults if a write targets a missing directory or a
read-only CD path.  This verification deliberately used only the precreated
`C:/Home` and `C:/Hermes/Apps/HermesBBS` directories, and checked both with
HRPC before writing.  No trial wrote to a missing directory or to the ISO
path, and the debugger is treated as a failure (not a pass) in the boot
checker.

## E. Research document

`docs/research/preinstalled-disk.md` covers qcow2 versus raw, the TinkerOS
MBR + FAT32 install layout, the existing installer automation, compression and
image size, and why `C:` persists without the CD, with sources.

## Notes

- The shipped image contains no test marker files.  All persistence and HRPC
  write tests ran on a copy.
- The ISO is the only install source; the boot path after installation is the
  TinkerOS MBR -> stage 2 -> partition boot record -> `Kernel.BIN.C` on `C:`.
- The ISO binary and the qcow2 are not tracked by git.
- No guest HolyC source was changed in this slice.  The 0.1.2 daemon bug
  remains present on the image and was routed around, not fixed.
