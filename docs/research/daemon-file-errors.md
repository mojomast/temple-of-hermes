# Hermes daemon file-I/O errors: research and design notes

Scope: the `HermesDaemon` COM1/HRPC file operations (`push`, `pull`,
`doc_write`, `doc_read`, `list`/`ls`, `stat`) in
`Adam/Hermes/Daemon.HC` and `Adam/Hermes/Files.HC`.  The released 0.1.2
live CD can enter the TinkerOS debugger when an HRPC write targets a
missing directory, an absent drive, or the read-only CD.  This note records
the kernel/TinkerOS contracts behind that failure and the guard design used
for 0.1.3.

Tree under study: Temple of Hermes `66a270746d2d157d7060c50d747c8a9f5ba4d50a`
(v0.1.2), whose `Kernel/` is the TinkerOS 5.20-rc10 base described in
`docs/ISO-BUILD.md`.  The stock CD used for builds is the public
`tinkeros/TinkerOS` 5.20-rc10 release (`docs/upstream/LinuxQEMU.md:11-13`).

## 1. How TempleOS/TinkerOS guards file I/O

### 1.1 Exceptions are non-local jumps with a per-task handler stack

`Kernel/KExcept.HC:85` defines `throw(ch,no_log,exit_unhandled)`.  A
`throw` records the character code in `Fs->except_ch`, walks
`Fs->next_except`, and transfers control to the innermost `try` frame.
`Kernel/KExcept.HC:104-112` shows the search: if `Fs->catch_except` is set,
the handler is taken; otherwise the frame is discarded and the search
continues.  If no frame catches it, `PutExcept(FALSE)` runs and
`Panic("Unhandled Exception")` is called.  That is the debugger path seen on
the live CD.

`Doc/HolyC.DD:230` documents the same contract for HolyC application code:
`try {} catch {}` with `Fs->except_ch`, and `Fs->catch_except=TRUE` inside
`catch` to stop the handler search.  A `catch` block that returns to normal
code must set `Fs->catch_except=TRUE`; otherwise the exception can continue
propagating.

`Adam/Hermes/Daemon.HC:42-77` already uses this pattern in `HermesEval`:
`try { ExePrint(...) } catch { Fs->catch_except=TRUE; ... PutExcept ... }`.
`HermesInit` likewise wraps `CommInit`/`CommInit8n1`
(`Adam/Hermes/Daemon.HC:494-500`).

### 1.2 Drive validation throws unless the caller opts out

`Kernel/BlkDev/DskDrv.HC:156` defines `DrvChk(dv,except=TRUE)`.  A null
drive pointer or a bad `dv_signature` is a `throw('Drv')` when `except` is
true; with `except=FALSE` it returns `NULL`.

`Kernel/BlkDev/DskDrv.HC:218` defines `Let2Drv(drv_let=0,except=TRUE)`:
it normalizes the letter with `Let2Let` (`:` means
`blkdev.boot_drv_let`, `~` means the home drive) and then calls
`DrvChk(dv,except)`.  The default is therefore the dangerous form: asking
for a drive letter that is not mounted throws.  On a live CD, `C:` is not
necessarily mounted (the build uses `T:` as the CD drive), so
`Let2Drv('C')` can throw before any directory is examined.

`Kernel/BlkDev/DskDrv.HC:238` defines
`DrvIsWritable(drv_let=0,except=FALSE)`.  It resolves the block device via
`Let2BlkDev` and returns `NULL` when the device is missing or has
`BDF_READ_ONLY`; only `except=TRUE` turns those cases into `throw('Drv')`.
This is the safe, non-throwing writability probe used by
`Adam/Hermes/StateDir.HC:33-36`
(`return DrvIsWritable(':',FALSE)!=NULL;`).

### 1.3 `DirContextNew` and `DirMk` are the sharp edges

`Kernel/BlkDev/DskDirContext.HC:28` defines `DirContextNew(mask,make_mask,
make_dirs,no_mask)`.  It can fail by returning `NULL` (invalid path), but
it also has unguarded kernel calls: `Let2Drv(*mask)` at line 47 (throws
when the letter is absent), `Cd(buf,make_dirs)` at line 68, and
`DirMk(buf)` at line 85.  With `make_dirs=TRUE` those calls can create
directories, which means they can also reach the block layer on a
read-only device.

`Kernel/BlkDev/DskDirB.HC:190` defines `DirMk`.  On ISO9660 it prints
`Not Writable` and returns `FALSE` (line 218); on RedSea/FAT32 it allocates
a cluster and writes directory blocks.  The write reaches
`Kernel/BlkDev/DskBlk.HC:109-110`, where `BDF_READ_ONLY` produces
`throw('BlkDev')`.  `BlkWrite` itself catches only around its own lock/body
and rethrows nothing, so the exception leaves the call stack at the
nearest enclosing `try` — which, before 0.1.3, was outside the daemon's
file operation or absent entirely.

`Kernel/BlkDev/FileSysRedSea.HC:386` defines `RedSeaDirNew`; when a parent
directory entry cannot be found it `throw('Drv')` at line 455.
`Kernel/BlkDev/FileSysRedSea.HC:566` defines `RedSeaFileWrite`, which
calls `Name2DirClus` first.  `Kernel/BlkDev/DskStrB.HC:10` defines
`Name2DirClus`; at line 45 it prints `File not found: "<dir>"` and returns
cluster 0 when a path component is missing.  Downstream RedSea code then
works with an invalid directory, or the earlier `Let2Drv`/`DrvChk` has
already thrown.  This is the `HermesHandleLine > FileWrite > DirContextNew
> Let2Drv > DrvChk` chain reported for 0.1.2.

### 1.4 Whole-file helpers do not add a guard

`Kernel/BlkDev/DskFile.HC:7` defines `FileRead`.  It calls
`DirContextNew` at lines 36 and 62 and prints `File not found` when the
read fails (line 86).  It does not wrap those calls in `try`.

`Kernel/BlkDev/DskFile.HC:110` defines `FileWrite`.  Its first action is
`DirContextNew(filename,FALSE,TRUE)` at line 116, i.e. `make_dirs=TRUE`.
The actual write dispatch is lines 129-138: RedSea and FAT32 call
`RedSeaFileWrite`/`FAT32FileWrite`, while ISO9660 prints `Not Writable`.
Because the parent-directory creation happens inside `DirContextNew`
before the filesystem switch, a missing parent or a read-only volume can
throw before `FileWrite` ever gets to return a negative value.  Checking
`wrote<0` after `FileWrite` is therefore insufficient; the call itself
must be inside `try`.

`Kernel/BlkDev/DskFind.HC:65` defines `FileFind`.  It safely tests an
absent drive with `Let2Drv(*filename,FALSE)` (line 72), and
`Kernel/BlkDev/DskFind.HC:32` defines `FilesFind`.  Their directory walk
still calls filesystem-specific find functions, so application code should
also guard them when input is untrusted.

## 2. CD / RedSea read-only semantics on the live disc

- The CD is mounted as TinkerOS's first CD drive.  `Kernel/KCfg.HC:252`
  labels it `First CD Drive:%C` with `'T'`, and `Kernel/KMain.HC:22` sets
  `kernel_cfg->mount_ide_auto_cd_let='T'` when the config leaves it unset.
  `Once.HC:36-39` prefers `::` (the boot drive) and then
  `T:/Hermes/Apps/Launcher/Run.HC`, confirming that the live disc's Hermes
  files live on the CD letter.
- `Kernel/BlkDev/DskBlkDev.HC:267-272` marks `BDT_ISO_FILE_READ` with
  `BDF_READ_ONLY`, and ATAPI/SATAPI devices with
  `BDF_REMOVABLE|BDF_READ_ONLY`.  `Kernel/BlkDev/DskBlk.HC:109-110` turns
  any write to such a device into `throw('BlkDev')`.
- `Adam/Hermes/StateDir.HC:1-7` states the practical consequence: "The
  live ISO has no writable C:", and an app that calls `DirMk("C:/Tmp")`
  dies before it can draw.  `HermesStateWritable` uses
  `DrvIsWritable(':',FALSE)` and `HermesStateRamDir` falls back to the
  `B:` RAM drive; every `DirMk`/probe write there is inside `try`
  (`Adam/Hermes/StateDir.HC:49-77`).
- RedSea (the TempleOS native filesystem) is writable only when its
  underlying block device is writable.  RedSea directory creation reaches
  `RedSeaDirNew`, and RedSea file creation reaches `RedSeaFileWrite` +
  `BlkWrite`.  A missing path component is reported by `Name2DirClus` as
  `File not found` and cluster 0; a read-only block device is reported as
  an exception.  ISO9660 instead refuses at the filesystem switch with
  `Not Writable` (`Kernel/BlkDev/DskFile.HC:136-137`,
  `Kernel/BlkDev/DskDirB.HC:216-218`).

Thus two distinct failure classes must be handled separately:

1. **Bad or absent drive/path**: `Let2Drv`/`DrvChk`/`DirContextNew` can
   throw `'Drv'`, or `Name2DirClus` can report a missing component.
2. **Read-only media**: `DrvIsWritable` returns `NULL`, and an attempted
   write can throw `'BlkDev'` from `BlkWrite`.

## 3. The daemon rule: validate, report, keep serving

A device daemon is a long-lived service.  An RPC peer can send any bytes;
bad input is expected, not exceptional.  The safe contract is:

1. Parse and bound the request before allocating or touching the
   filesystem (length, drive letter, path shape).
2. Reject unsupported or unsafe requests with a machine-readable error.
3. Perform only guarded kernel calls (`try`/`catch` around `FileRead`,
   `FileWrite`, `DirMk`, `FilesFind`, `DocRead`).
4. Convert any escaped exception into a structured reply and return to the
   request loop.  The daemon task must never reach `Panic("Unhandled
   Exception")` because of a client request.

The existing 0.1.0/0.1.2 protocol already has the right envelope:
`HRPL <id> ok|err <len>` (`Adam/Hermes/Protocol.HC:23-43`).  What was
missing was a stable error body and guards on every file branch.

## 4. What the 0.1.2 tree already does, and the gaps

### Existing guards

- `Adam/Hermes/StateDir.HC`: correct writability probe and `try` around
  every `DirMk`/`FileWrite` probe.  `HermesStateDirFor` chooses a preferred
  directory only when the boot drive is writable and otherwise uses the
  RAM drive.
- `Adam/Hermes/Files.HC:10-31`: `HermesListDir` wraps `FilesFind` and its
  directory walk in `try`/`catch`.  This prevents a list crash but hides
  the error.
- `Adam/Hermes/Daemon.HC:42-77`: `HermesEval` catches compile/eval
  exceptions and produces a JSON error object.
- `Adam/Hermes/Daemon.HC:494-500`: `HermesInit` catches serial-init
  failures.
- `Adam/Hermes/Events.HC:113-129`: task/window polling guards `StrPrint`
  and window checks.

### Gaps in 0.1.2

- `Adam/Hermes/Daemon.HC` `doc_write` branch (`FileWrite` at line 324) and
  `push` branch (`FileWrite` at line 388) call `FileWrite` with no `try`.
  A `throw('Drv')` or `throw('BlkDev')` from `DirContextNew`/`BlkWrite`
  escapes to `HermesHandleLine`.
- `pull` calls `FileRead` unguarded and only tests `!data`/`size`
  afterwards.
- `HermesHandleLine` (`Adam/Hermes/Daemon.HC:417-446`) calls
  `HermesHandle` with no `try`; the daemon loop
  (`Adam/Hermes/Daemon.HC:449-489`) has no last-resort catch either.
- `Adam/Hermes/Files.HC:3-36` `HermesListDir` does not validate the drive
  or path and returns `[]` for both "empty" and "failed".
- `Adam/Hermes/Files.HC:62-83` `HermesStatJSON` calls `FileFind` outside
  any `try`.
- `Adam/Hermes/Files.HC:85-121` `HermesDocReadJSON` calls `DocRead`
  outside any `try` and does not validate the drive.
- Writes do not check `DrvIsWritable` first and do not distinguish
  `bad_drive`, `missing_dir`, `read_only`, `too_large`, and generic
  `write_failed`.
- `HermesHandleLine` rejects an oversized length with the bare string
  `"len"` (`Adam/Hermes/Daemon.HC:432-436`), which is not a parseable
  structured error.
- The payload read loop calls `HermesGetChar` (`Adam/Hermes/Daemon.HC:441-446`)
  with no `try`.  `HermesGetChar` is `CommGetChar` on COM1, and
  `Adam/Device/Comm.HC:226-238` throws `'ComErr'` when a byte does not
  arrive inside the serial timeout.  A truncated or over-fast push therefore
  reaches `Panic("Unhandled Exception")` even when the file path itself is
  valid; this is a second, independent daemon-crash path.

## 5. 0.1.3 design

`Adam/Hermes/FileGuard.HC` adds:

- `HermesFileDriveOf` / `HermesFileDriveOk` / `HermesFileDriveWritable`:
  letter parsing, `Let2Drv(letter,FALSE)` existence checks, and
  `DrvIsWritable(letter,FALSE)` for write permission.  `B:` is created
  through `HermesStateMakeRam` when needed.
- Path checks: non-empty, no `..` component, valid drive, and safe parent
  probing with `FileFind(...,FUF_JUST_DIRS)`.
- `HermesFileMkParents`: creates only missing parent components and only
  after the writable check; every `DirMk` is wrapped.
- Guarded primitives: `HermesFileWriteSafe`, `HermesFileReadSafe`,
  `HermesFileFindSafe`, `HermesDirMkSafe`, `HermesDocReadSafe`.
- `HermesFileErrJSON`: one stable body shape,
  `{"ok":0,"error":"<code>","code":"<code>","op":"<op>",
  "drive":"<letter>","path":"<escaped path>"}`, with codes
  `bad_drive`, `bad_path`, `missing_dir`, `read_only`, `too_large`,
  `missing_file`, `write_failed`, `read_failed`, `short_read`, and
  `exception`.
- `HermesFileWriteJSON`, `HermesFilePullJSON`, and read-side helpers that
  return either a success object or the structured error object and set a
  boolean `ok` flag.

`Adam/Hermes/Daemon.HC` then:

- uses the helpers for `push`, `doc_write`, `pull`, `doc_read`, `list`,
  and `stat`;
- replies with `HRPL ... err` and the JSON body for any refused file op;
- wraps the payload read loop and the whole `HermesHandle` dispatch in
  `try`/`catch`, and wraps the call from `HermesHandleLine`, so a serial
  timeout, a short frame, or any other unexpected exception still produces
  an error reply and the daemon loop continues;
- returns `too_large` JSON instead of the bare `"len"` string.

`Adam/Hermes/Files.HC` keeps its public return shapes for normal calls
(`list` returns an array, `stat` returns the old object) but routes both
through the guarded validation and error helpers.

The version strings become `0.1.3` in `Adam/Hermes/VERSION` and
`HERMES_VERSION` in `Adam/Hermes/Glbls.HC`, so a rebuilt ISO is not
confused with 0.1.2 media that still emits `TempleOfHermes/0.1.0`
beacons.

## 6. Verification expectations

Host-side `scripts/test_daemon_file_errors.py` and guest-side
`Adam/Hermes/FileErrorsTest.HC` exercise:

| Case | Example | Expected structured code | Daemon after |
| --- | --- | --- | --- |
| missing directory | `T:/Hermes/Apps/NoSuchDir/token.txt` | `missing_dir` | ping ok |
| read-only CD | `T:/Hermes/Apps/HermesBBS/token.txt` | `read_only` | ping ok |
| writable RAM drive | `B:/Tmp/hermes-daemon-fix-0.1.3.txt` | success (`ok:1`) | ping ok |
| oversized payload | `HREQ n push 262145` | `too_large` | ping ok |
| short serial frame | body not delivered before `ComErr` | `short_read` | ping ok |
| bad drive letter | `Q:/Hermes/no.txt` | `bad_drive` | ping ok |

A pass also requires that the live-CD screenshot/OCR after the matrix does
not contain `Unhandled Exception` or the debugger, and that COM2 echo still
works independently of COM1.
