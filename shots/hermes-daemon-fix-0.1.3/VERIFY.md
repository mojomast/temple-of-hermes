# TempleOfHermes-0.1.3 verification

- ISO: `dist/TempleOfHermes-0.1.3.ISO`
- Size: 14,045,184 bytes
- SHA256: `bd39456ce4eaa2f1116b44c75899aab47e40172f6539e21697d34e704c28c698`
- ISO9660 volume id: `THE_TEMPLE_OF_HERMES`
- Source: Temple of Hermes `66a270746d2d157d7060c50d747c8a9f5ba4d50a`
  (v0.1.2, merge of PR #1), packed HEAD used directly for work branch
  `hermes/daemon-fix-0.1.3` (`git checkout -B hermes/daemon-fix-0.1.3 HEAD`).
- Research: `docs/research/daemon-file-errors.md`
- Build: guest `Adam/Hermes/MakeDistro.HC` -> `BootDVDIns` -> `RedSeaISO`
  from a stock TinkerOS 5.20-rc10 install with a FAT32 overlay
  (`D:/RUN.HC`, 256 files copied to `C:`). No xorriso and no stock-ISO
  remaster.
- Base CD: TinkerOS 5.20-rc10, sha256
  `feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4`.
- All live-CD checks used QEMU TCG, `-display none -nic none
  -machine pc,kernel-irqchip=off`, with no writable guest disk.

The in-guest daemon version is `0.1.3` (`HBEACON TempleOfHermes/0.1.3`,
ping/`sysinfo` version `0.1.3`).  The launcher's cosmetic caption and
`Once.HC` banner still say `v0.1.2`; those files are outside this task's
assigned file set.  The daemon-visible version is the 0.1.3 value.

## 1. Boot reliability and clean overlay

20 independent boots, each a new VM with no disk, waiting up to 75 s for the
launcher and the HRPC `windows` list:

- **20/20 launcher passes** (target 20/20).
- Times: minimum 11.8 s, maximum 12.3 s.
- A pass requires only the `Hermes Apps` window: no AutoComplete / System
  Keys guide, no Tour/Install terminal, and no other window overlapping the
  icon grid.
- Log: `boot-trials.log`; data: `boot-trials.json`.

The overlay printed `OVERLAY DONE`, and each overlaid destination's
compressed `.Z` twin was deleted by the same pass, so the 0.1.3 HolyC loads
instead of a stale compressed copy.

## 2. Home screen

- `02-home-launcher.png`: full-screen borderless launcher, 18 entries in a
  6x3 grid, unique key hints, ASCII footer help line.
- `01-boot-splash.png`: the built disc boot screen.

## 3. App launch matrix

Every entry was driven from the home screen with a real mouse click and with
its shortcut key.  `return` means the clean, focused `Hermes Apps` launcher
was visible again with no overlapping window.  `diff` is the sampled pixel
difference from the pre-launch home shot.

| App | Click | Key | Return (click/key) | Click diff | Key diff | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Temple | PASS | PASS | clean launcher / clean launcher | 0.00 | 0.00 | `app-temple-*.png`, `temple-check.json` |
| Hermes Chat | PASS | PASS | PASS/PASS | 0.96 | 0.96 | `app-hermes-chat-*.png`, `return-hermes-chat-*.png` |
| WorldSim | PASS | PASS | PASS/PASS | 0.84 | 0.84 | `app-worldsim-*.png`, `return-worldsim-*.png` |
| Codex | PASS | PASS | PASS/PASS | 0.92 | 0.92 | `app-codex-*.png`, `return-codex-*.png` |
| Psyche | PASS | PASS | PASS/PASS | 0.97 | 0.97 | `app-psyche-*.png`, `return-psyche-*.png` |
| Capybara | PASS | PASS | PASS/PASS | 0.93 | 0.93 | `app-capybara-*.png`, `return-capybara-*.png` |
| Messenger | PASS | PASS | PASS/PASS | 0.25 | 0.25 | `app-messenger-*.png`, `return-messenger-*.png` |
| BBS | PASS | PASS | PASS/PASS | 0.13 | 0.14 | `app-bbs-*.png`, `return-bbs-*.png` |
| Threshold | PASS | PASS | PASS/PASS | 0.18 | 0.18 | `app-threshold-*.png`, `return-threshold-*.png` |
| Dojo | PASS | PASS | PASS/PASS | 0.82 | 0.82 | `app-dojo-*.png`, `return-dojo-*.png` |
| Offerings | PASS | PASS | PASS/PASS | 0.84 | 0.84 | `app-offerings-*.png`, `return-offerings-*.png` |
| Southpaw | PASS | PASS | PASS/PASS | 0.84 | 0.83 | `app-southpaw-*.png`, `return-southpaw-*.png` |
| Modem / Net | PASS | PASS | PASS/PASS | 0.97 | 0.97 | `app-modem-net-*.png`, `return-modem-net-*.png` |
| Caduceus | PASS | PASS | PASS/PASS | 0.76 | 0.76 | `app-caduceus-*.png`, `return-caduceus-*.png` |
| Token Rain | PASS | PASS | PASS/PASS | 0.25 | 0.25 | `app-token-rain-*.png`, `return-token-rain-*.png` |
| Spoon | PASS | PASS | PASS/PASS | 0.30 | 0.30 | `app-spoon-*.png`, `return-spoon-*.png` |
| Dojo Duel | PASS | PASS | PASS/PASS | 0.16 | 0.16 | `app-dojo-duel-*.png`, `return-dojo-duel-*.png` |
| About | PASS | PASS | PASS/PASS | 0.97 | 0.97 | `app-about-*.png`, `return-about-*.png` |

**All 18 entries passed.**  The 17 non-Temple entries launched from both a
mouse click and a key and returned to the launcher.  Temple stays on the
home screen by design; both click and `T` left the clean launcher visible.
About opened the About/help view and returned.

## 4. COM2 echo

`net-echo.log` records the local unix-socket stub.  The guest sent
`HERMES-NET-ECHO-01` (18 bytes), the stub echoed it, and the guest showed
`ECHO OK` in `19-net-echo.png`.  COM1 stayed the Hermes HRPC console.  No
BBS, VPS, public host, or external network destination was contacted.

## 5. Daemon file-error matrix (live CD)

`scripts/test_daemon_file_errors.py` ran against the accepted ISO over COM1.
Each case had to return a structured `HRPL err` body (or a documented B:
success), and the daemon had to answer a follow-up `ping` with
`HRPL ok` / `pong:1` / version `0.1.3`.

| Case | Op | Path | Reply | Code | Ping after |
| --- | --- | --- | --- | --- | --- |
| missing directory | push | `T:/Hermes/Apps/__HERMES_NO_SUCH_DIR__/marker.txt` | err | `missing_dir` | ok |
| released bug path (C: absent on CD) | push | `C:/Hermes/Apps/HermesBBS/token.txt` | err | `bad_drive` | ok |
| read-only CD | push | `T:/Hermes/Apps/Launcher/hermes-daemon-0.1.3-marker.txt` | err | `read_only` | ok |
| writable B: RAM | push | `B:/Tmp/hermes-daemon-fix-0.1.3-marker.txt` | ok | — | ok |
| writable B: RAM pull | pull | same file | ok | — | ok |
| oversized payload | push | declared length 262145, no body | err | `too_large` | ok |
| bad drive letter | push | `Q:/Hermes/marker.txt` | err | `bad_drive` | ok |

- Result: **7/7**; `file-errors.json`, `file-errors.log`,
  `file-errors-com1.log`.
- The post-matrix screen (`file-errors-after.png`) OCR has no
  `Unhandled Exception` or debugger text.
- Extra serial-frame guard: a 4 KB legal-looking push larger than the QEMU
  serial delivery window returned `short_read` and the follow-up ping still
  answered `ok`; the daemon did not enter the debugger.

Guest-side `Adam/Hermes/FileErrorsTest.HC` was executed from the accepted
CD with `ExeFile("T:/Adam/Hermes/FileErrorsTest.HC")`.  It reported:

```
HERMES FILE ERRORS TEST (0.1.3)
PASS missing_dir
PASS cd_read_only
PASS ram_write
PASS too_large
PASS bad_drive
PASS ram_readback
HERMES FILE ERRORS TEST PASS
```

Evidence: `guest-file-errors.json`, `guest-file-errors-com1.log`.

## 6. Shots and checks

All 74 PNGs in this directory are 640x480, mode P, palette indices 0-15,
with 0 off-palette pixels:

- `PIL-CHECKS.txt`: `RESULT PASS shots=74`.
- `OCR-CHECKS.txt`: `RESULT PASS shots=74`; no `Except:`, `ERROR:`,
  `Undefined identifier`, `Fault:`, `Fatal`, `Unhandled Exception`, or
  `Panic` text.

No image was opened, previewed, or viewed in-model.  All checks used PIL and
the in-repo 8x8 glyph OCR.

## 7. Notes

- `docs/research/daemon-file-errors.md` records the kernel/TinkerOS
  contracts, live-CD read-only semantics, existing guards, gaps, and the
  0.1.3 design.
- The ISO binary is gitignored and is not committed, released, or deployed.
- No sandbox commit, push, merge, tag, release, or branch delete was made.
  The work branch is `hermes/daemon-fix-0.1.3`; changes are uncommitted.
