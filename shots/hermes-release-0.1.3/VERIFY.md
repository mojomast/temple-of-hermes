# Temple of Hermes 0.1.3 release verification

Source tree: `origin/main` at
`0a6c335b1273ddeb4f525e3cc5cc6b8a29dae809` (the 0.1.3 integration merge:
daemon file-op fix, 0.1.3 banners, preinstalled-disk build script,
Adam/Hermes/Home.HC home journal, BBS community server).

Work branch: `hermes/release-0.1.3`, created from that packed `HEAD` only.
Nothing is committed; the ISO, disk, and evidence are produced from the
uncommitted working tree and left uncommitted for the launcher patch.

All QEMU work used TCG with `-display none -nic none
-machine pc,kernel-irqchip=off`. No image was opened or viewed in-model; the
screenshots use the in-repo 8x8 glyph OCR and PIL palette checks only.

## Release artifacts

| Artifact | Bytes | SHA-256 |
| --- | --- | --- |
| `TempleOfHermes-0.1.3.ISO` | 14,053,376 | `fbaa3d6f0a8f9190f295e933c32cb833a61b3cb43a708309acb6c98ff51ac4fd` |
| `TempleOfHermes-0.1.3-disk.qcow2` | 11,107,840 | `d81a3c189093bd0edddad50b7a55d6582d0490204d63720e14fc5fb9d901f1aa` |

Both were copied to `/output` (`READY-ISO`, `READY-DISK`) and are listed in
`/output/SHA256SUMS` and `shots/hermes-release-0.1.3/SHA256SUMS`. The ISO
image is gitignored; neither binary is in git.

## 1. ISO build

Method: `docs/ISO-BUILD.md`, unchanged: install stock TinkerOS 5.20-rc10 to a
4 GiB qcow2, deliver the Hermes tree with a 64 MiB FAT32 overlay
(`D:/RUN.HC`), then run the guest's own
`Adam/Hermes/MakeDistro.HC` -> `BootDVDIns` -> `RedSeaISO`. No xorriso, no
stock remaster. Host extraction used the RedSea ISO names through
`scripts/fat32_read.extract`.

- Base CD: TinkerOS 5.20-rc10, SHA-256
  `feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4`.
- Overlay: 258 files copied to `C:`, `OVERLAY DONE`, then
  `Temple of Hermes ISO written to /Tmp/TempleOfHermes.ISO.C`.
- ISO9660 volume id: `THE_TEMPLE_OF_HERMES`.
- The build script's fixed output name is `TempleOfHermes-0.1.2.ISO`; the
  sealed bytes were copied unchanged to the release name
  `TempleOfHermes-0.1.3.ISO`, and the SHA-256 above is the built image.

The 0.1.3 merge added `Adam/Hermes/Home.HC` and
`Adam/Hermes/FileGuard.HC` to the daemon include chain
(`Adam/Hermes/Load.HC` includes both), plus the guest test scripts
`HomeTest.HC` and `FileErrorsTest.HC`. `scripts/build_iso.py` still carries
the 0.1.2 overlay list, so the release build used
`shots/hermes-release-0.1.3/build_iso_013.py`, a wrapper that appends those
four source files to the module's `OVERLAY_PATHS` and then calls
`build_iso.main()` unchanged. No build script source was modified, and the
in-guest MakeDistro/RedSeaISO path is identical.

### Home.HC inside the ISO

Checked twice, host-side and in-guest:

- Host-side, the sealed ISO contains the Home.HC source text (`U8 *HomeInit(`
  and the `HERMES_HOME_HC` guard) and no `v0.1.2` string.
- In-guest (`iso/check_iso_home.py`) a live boot pulls the files from the
  disc itself through the daemon:

| File | Result |
| --- | --- |
| `T:/Adam/Hermes/Home.HC` | 4,077 bytes, SHA-256 `496b817469e1b1362700dc7b7d8f93b84d7bdec8c1462f685c4cf6863ab11f7f`, byte-identical to `Adam/Hermes/Home.HC` |
| `T:/Adam/Hermes/Load.HC` | 286 bytes, SHA-256 `643e4bd484eff70e114e7c62ef5f274ba868e2c3113689e62e29355ce315981e`, exactly one `#include "Home"` |
| `T:/Adam/Hermes/VERSION` | `0.1.3` |
| `T:/Hermes/Apps/Registry.HC` | 4,557 bytes present |

Evidence: `iso/iso-home-check.json`, `iso/iso-home-check-com1.log`,
`iso/iso-Home.HC`, `iso/iso-Load.HC`.

## 2. ISO acceptance (live CD, no writable disk)

### A. 20 independent launcher boots

Each trial is a new VM with no disk, waiting up to 75 s. A pass requires the
`Hermes Apps` window and no AutoComplete/System Keys guide, Tour/Install
terminal, debugger, or other window over the icon grid.

- **20/20 passed**; min 12.2 s, median 13.2 s, max 16.9 s.
- OCR of `02-home-launcher.png`:
  `THE TEMPLE OF HERMES  v0.1.3` and `18 apps and games`.
- Evidence: `iso/boot-trials.json`, `iso/boot-trials.log`.

### B. All 18 launcher entries

Every entry was opened with a real mouse click and with its shortcut key, then
returned to the clean launcher. `diff` is the sampled pixel difference from
the pre-launch home screen.

| Entry | Click | Key | Return | Click diff | Key diff | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Temple | PASS | PASS | clean launcher | 0.00 | 0.00 | `app-temple-*.png`, `temple-check.json` |
| Hermes Chat | PASS | PASS | PASS | 0.96 | 0.96 | `app-hermes-chat-*.png` |
| WorldSim | PASS | PASS | PASS | 0.84 | 0.84 | `app-worldsim-*.png` |
| Codex | PASS | PASS | PASS | 0.92 | 0.92 | `app-codex-*.png` |
| Psyche | PASS | PASS | PASS | 0.97 | 0.97 | `app-psyche-*.png` |
| Capybara | PASS | PASS | PASS | 0.93 | 0.93 | `app-capybara-*.png` |
| Messenger | PASS | PASS | PASS | 0.25 | 0.25 | `app-messenger-*.png` |
| BBS | PASS | PASS | PASS | 0.14 | 0.14 | `app-bbs-*.png` |
| Threshold | PASS | PASS | PASS | 0.18 | 0.18 | `app-threshold-*.png` |
| Dojo | PASS | PASS | PASS | 0.82 | 0.82 | `app-dojo-*.png` |
| Offerings | PASS | PASS | PASS | 0.84 | 0.84 | `app-offerings-*.png` |
| Southpaw | PASS | PASS | PASS | 0.84 | 0.84 | `app-southpaw-*.png` |
| Modem / Net | PASS | PASS | PASS | 0.97 | 0.97 | `app-modem-net-*.png` |
| Caduceus | PASS | PASS | PASS | 0.76 | 0.76 | `app-caduceus-*.png` |
| Token Rain | PASS | PASS | PASS | 0.25 | 0.25 | `app-token-rain-*.png` |
| Spoon | PASS | PASS | PASS | 0.30 | 0.30 | `app-spoon-*.png` |
| Dojo Duel | PASS | PASS | PASS | 0.16 | 0.16 | `app-dojo-duel-*.png` |
| About | PASS | PASS | PASS | 0.97 | 0.97 | `app-about-*.png` |

**18/18 entries passed both input methods.** Temple intentionally leaves the
home screen visible; the clean launcher is the expected result. The other 17
opened their own window and returned. Evidence: `iso/app-results.json`,
`iso/capture.log`, `iso/temple-check.json`.

### C. COM2 echo

`iso/net-echo.log` is a local unix-socket stub; no external network was
contacted. The guest sent `HERMES-NET-ECHO-01` (18 bytes), the stub echoed it,
and the guest displayed `ECHO OK` (`iso/19-net-echo.png`). COM1 remained the
Hermes HRPC console.

### D. Daemon file-error matrix (live CD)

`iso/test_daemon_file_errors.py` (copy of
`scripts/test_daemon_file_errors.py`) ran against the accepted ISO over COM1.
Every case returned a structured `HRPL`, and every follow-up `ping` answered
`pong:1` with version `0.1.3`.

| Case | Op | Path | Reply | Code | Ping after |
| --- | --- | --- | --- | --- | --- |
| missing directory | push | `T:/Hermes/Apps/__HERMES_NO_SUCH_DIR__/marker.txt` | err | `missing_dir` | ok |
| released bug path (C: absent on CD) | push | `C:/Hermes/Apps/HermesBBS/token.txt` | err | `bad_drive` | ok |
| read-only CD | push | `T:/Hermes/Apps/Launcher/hermes-daemon-0.1.3-marker.txt` | err | `read_only` | ok |
| writable B: RAM | push | `B:/Tmp/hermes-daemon-fix-0.1.3-marker.txt` | ok | — | ok |
| writable B: RAM pull | pull | same file | ok | — | ok |
| oversized payload | push | declared length 262145, no body | err | `too_large` | ok |
| bad drive letter | push | `Q:/Hermes/marker.txt` | err | `bad_drive` | ok |

**7/7 passed.** The post-matrix screen has no `Unhandled Exception`, `Panic`,
`Except:`, or debugger text. Evidence: `iso/file-errors.json`,
`iso/file-errors.log`, `iso/file-errors-after.png`.

### Shot checks

40 saved PNGs, all 640x480 mode P, palette indices 0-15, 0 off-palette
(`iso/PIL-CHECKS.txt`: `RESULT PASS shots=40`). Text-only OCR found no
exception strings (`iso/OCR-CHECKS.txt`: `RESULT PASS shots=40`), including
`THE TEMPLE OF HERMES v0.1.3` on the home shot.

## 3. Disk image build

Built from the accepted ISO with the existing script, no source rewrite:

```
python3 scripts/build_disk_image.py \
  --iso dist/TempleOfHermes-0.1.3.ISO \
  --sha256 fbaa3d6f0a8f9190f295e933c32cb833a61b3cb43a708309acb6c98ff51ac4fd \
  --iso-size 14053376 \
  --output dist/TempleOfHermes-0.1.3-disk.qcow2
```

The script verified the ISO and volume id, booted the ISO, drove the ISO's own
`DoInstall(TRUE)` prompts, copied the root plain `.HC`/`.DD`, `Home`, and
`Hermes` trees, created `C:/Home` and `C:/Hermes/Apps/HermesBBS`, verified the
installed FAT32 tree, and patched the TinkerOS stage-2 menu to select the
installed Drive C automatically. QEMU booted with no keypress.

| Property | Value |
| --- | --- |
| Format | qcow2, zlib-compressed clusters, 64 KiB cluster |
| Virtual size | 4,294,967,296 bytes (4 GiB) |
| File size | 11,107,840 bytes |
| SHA-256 | `d81a3c189093bd0edddad50b7a55d6582d0490204d63720e14fc5fb9d901f1aa` |
| ISO used | `fbaa3d6f0a8f9190f295e933c32cb833a61b3cb43a708309acb6c98ff51ac4fd` |
| Layout | MBR, active FAT32 type 0x0B at LBA 63, TinkerOS kernel |
| `qemu-img check` | No errors; 83.72% compressed clusters |

`C:/Home` and `C:/Hermes/Apps/HermesBBS` are precreated in the image and were
observed through HRPC at runtime. No `scripts/build_disk_image.py` or
`scripts/test_disk_image.py` change was needed for 0.1.3.

## 4. Disk verification (throwaway copies only)

All trials booted `run/release-disk-test/boot-test.qcow2` or
`run/release-disk-extras/extras.qcow2`, copies of the sealed image. The sealed
`/output` image was hashed before and after and is unchanged.

### A. 20 independent cold boots, no CD

New VM per trial, up to 75 s, exactly one visible window titled `Hermes Apps`.

- **20/20 passed**; min 6.9 s, median 10.3 s, max 10.8 s.
- Evidence: `disk/boot-trials.json`, `disk/boot-trials.log`,
  `disk/summary.json`.

### B. Persistence across reboot

Marker files written through HRPC to the precreated directories, then read
back after a no-CD reboot:

| Path | Bytes | Before | After reboot |
| --- | --- | --- | --- |
| `C:/Home/TEST-MARKER.TXT` | 12 | PASS | PASS, byte-identical |
| `C:/Hermes/Apps/HermesBBS/TEST-TOKEN.TXT` | 11 | PASS | PASS, byte-identical |

`ping` answered `ok` in both phases. Evidence: `disk/persistence.json`,
`disk/persistence-launcher.png`.

### C. HRPC writes on C: and structured errors

`disk/test_release_extras.py` pushed then pulled a marker through HRPC on
`C:` and pinged OK. The 0.1.3 daemon auto-creates missing parent directories
on a writable drive (recorded as a positive check). On a boot with the release
ISO attached read-only as `T:` (Drive C still boots), the guard returned the
structured errors:

| Case | Reply | Code | Ping after |
| --- | --- | --- | --- |
| missing directory on read-only T: | err | `missing_dir` | ok, `pong:1`, 0.1.3 |
| write into read-only T: | err | `read_only` | ok, `pong:1`, 0.1.3 |

### D. Home journal on C: with persistence

No `Home.HC` was pushed. The disk image already contains
`C:/Adam/Hermes/Home.HC` (4,077 bytes, byte-identical to the tree) and
`C:/Adam/Hermes/Load.HC` with its `#include "Home"`. Calling
`HomeInit("hermes",'C')` through the daemon's global symbol table succeeded
with `OK C:/Home/hermes`, proving the helper was compiled from the image.

| Step | Result |
| --- | --- |
| `HomeInit("hermes",'C')` (no push) | `OK C:/Home/hermes` |
| Layout | `C:/Home/hermes/Src/` created; `JOURNAL.TXT` and `PROJECTS.TXT` written by the helpers |
| Src marker | `Src/KEEP.TXT` 13 bytes written and read back |
| Journal entry 1 | `2026-11-11 23:46 release journal entry one` |
| Journal entry 2 | `2026-11-11 23:46 release journal entry two` |
| `ProjectSet` | `Current: Temple of Hermes 0.1.3` / `Next: Verify home journal on C` |
| Read back before reboot | 2 lines, valid `YYYY-MM-DD HH:MM <text>`, guest timestamp UTC skew 34 s |
| Reboot, no CD | `JOURNAL.TXT` SHA-256 unchanged (`9398d8cb...`), `PROJECTS.TXT` unchanged (`30801018...`), `Src/KEEP.TXT` 13 bytes byte-identical |
| `HomeInit` + further append after reboot | 2 -> 3 lines, prior bytes are an exact prefix, `post reboot append` present |
| `ProjectShow` after reboot | ok |
| Final ping | ok, `pong:1`, 0.1.3 |

The extras harness passed 23/23 checks with the sealed image unchanged.
Evidence: `disk/extras.json`, `disk/extras.log`, `disk/journal-phase1.png`,
`disk/journal-phase2.png`, `disk/errors-phase3.png`.

### Sealed image unchanged

`sha256sum /output/TempleOfHermes-0.1.3-disk.qcow2` before and after all disk
tests: `d81a3c189093bd0edddad50b7a55d6582d0490204d63720e14fc5fb9d901f1aa`.
`disk/summary.json` and `disk/extras.json` both report
`source_unchanged: true`.

## 5. Notes

- The 20/20 ISO and disk boot evidence uses independent VMs; the disk trials
  share one booted qcow2 copy but each uses a fresh VM, and the sealed image
  is never booted.
- No BBS, VPS, public host, or external network destination was contacted;
  COM2 is a local unix-socket stub only.
- No commit, push, merge, tag, release, or branch delete was made. The only
  branch created is `hermes/release-0.1.3`, from the packed `HEAD`.
- ISO and qcow2 binaries are gitignored and not in git. The release evidence
  contains only text, JSON, and 640x480 palette PNGs.
- Figure names in the apps are characters from the Nous universe; all game
  and app text is original to this tree.
