# TempleOfHermes-0.1.3 verification

- ISO: `dist/TempleOfHermes-0.1.3.ISO`
- Size: 14,045,184 bytes
- SHA256: `bb8cde023b76cb75e726ee6169a6b35bcb2a06b2433a25e4d9707b892d203f6f`
- ISO9660 volume id: `THE_TEMPLE_OF_HERMES`
- Source: Temple of Hermes `66a270746d2d157d7060c50d747c8a9f5ba4d50a`
  (v0.1.2 merge of PR #1); packed branch `hermes/daemon-fix-0.1.3` at
  `2071daa299419aa125c1a42fc2ba59a4c6b47ca2` (in-guest version 0.1.3).
- Research: `docs/research/daemon-file-errors.md`
- Build: guest `Adam/Hermes/MakeDistro.HC` -> `BootDVDIns` -> `RedSeaISO`
  from a stock TinkerOS 5.20-rc10 install with a FAT32 overlay
  (`D:/RUN.HC`, 256 files copied to `C:`), per `docs/ISO-BUILD.md`.
  No xorriso and no stock-ISO remaster.
- Base CD: TinkerOS 5.20-rc10, sha256
  `feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4`.
- In-guest daemon: `HBEACON TempleOfHermes/0.1.3`; ping and `sysinfo`
  report version `0.1.3`.
- Banners: `Once.HC`, `Hermes/Apps/Launcher/Load.HC`, `Doc/Start.DD`, and
  `Doc/AboutHermes.DD` now say `0.1.3`. The built ISO contains no
  `v0.1.2` string. OCR of `02-home-launcher.png` reads
  `THE TEMPLE OF HERMES  v0.1.3`; OCR of `03-startup-banner.png` reads
  `THE TEMPLE OF HERMES  v0.1.3` and
  `Version 0.1.3 - TinkerOS 5.200 base`.

All live-CD checks used QEMU TCG with `-display none -nic none
-machine pc,kernel-irqchip=off` and no writable guest disk.

## 1. Boot reliability and clean overlay

20 independent boots, each a new VM with no disk, waiting up to 75 s for the
launcher and the HRPC `windows` list:

- **20/20 launcher passes** (target 20/20).
- Times: minimum 11.7 s, maximum 12.0 s.
- A pass requires only the `Hermes Apps` window: no AutoComplete / System
  Keys guide, no Tour/Install terminal, and no other window overlapping the
  icon grid.
- Log: `boot-trials.log`; data: `boot-trials.json`.

## 2. Home screen

- `02-home-launcher.png`: full-screen borderless launcher, 18 entries in a
  6x3 grid, unique key hints, ASCII footer help line, caption
  `THE TEMPLE OF HERMES  v0.1.3`.
- `01-boot-splash.png`: the built disc boot screen.
- `03-startup-banner.png`: startup doc/terminal view showing version 0.1.3.

## 3. App launch matrix

Every entry was driven from the home screen with a real mouse click and with
its shortcut key. `return` means the clean, focused `Hermes Apps` launcher
was visible again with no overlapping window. `diff` is the sampled pixel
difference from the pre-launch home shot.

| App | Click | Key | Return (click/key) | Click diff | Key diff | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Temple | PASS | PASS | clean launcher / clean launcher | 0.00 | 0.00 | `app-temple-*.png`, `temple-check.json` |
| Hermes Chat | PASS | PASS | PASS/PASS | 0.96 | 0.96 | `app-hermes-chat-*.png` |
| WorldSim | PASS | PASS | PASS/PASS | 0.84 | 0.84 | `app-worldsim-*.png` |
| Codex | PASS | PASS | PASS/PASS | 0.92 | 0.92 | `app-codex-*.png` |
| Psyche | PASS | PASS | PASS/PASS | 0.97 | 0.97 | `app-psyche-*.png` |
| Capybara | PASS | PASS | PASS/PASS | 0.93 | 0.93 | `app-capybara-*.png` |
| Messenger | PASS | PASS | PASS/PASS | 0.25 | 0.25 | `app-messenger-*.png` |
| BBS | PASS | PASS | PASS/PASS | 0.14 | 0.13 | `app-bbs-*.png` |
| Threshold | PASS | PASS | PASS/PASS | 0.18 | 0.18 | `app-threshold-*.png` |
| Dojo | PASS | PASS | PASS/PASS | 0.82 | 0.82 | `app-dojo-*.png` |
| Offerings | PASS | PASS | PASS/PASS | 0.84 | 0.84 | `app-offerings-*.png` |
| Southpaw | PASS | PASS | PASS/PASS | 0.84 | 0.83 | `app-southpaw-*.png` |
| Modem / Net | PASS | PASS | PASS/PASS | 0.97 | 0.97 | `app-modem-net-*.png` |
| Caduceus | PASS | PASS | PASS/PASS | 0.76 | 0.76 | `app-caduceus-*.png` |
| Token Rain | PASS | PASS | PASS/PASS | 0.25 | 0.25 | `app-token-rain-*.png` |
| Spoon | PASS | PASS | PASS/PASS | 0.30 | 0.30 | `app-spoon-*.png` |
| Dojo Duel | PASS | PASS | PASS/PASS | 0.16 | 0.16 | `app-dojo-duel-*.png` |
| About | PASS | PASS | PASS/PASS | 0.97 | 0.97 | `app-about-*.png` |

**All 18 entries passed.** The 17 non-Temple entries launched from both a
mouse click and a key and returned to the launcher. Temple stays on the
home screen by design; both click and `T` left the clean launcher visible.
About opened the About/help view and returned.

## 4. COM2 echo

`net-echo.log` records the local unix-socket stub. The guest sent
`HERMES-NET-ECHO-01` (18 bytes), the stub echoed it, and the guest showed
`ECHO OK` in `19-net-echo.png`. COM1 stayed the Hermes HRPC console. No
BBS, VPS, public host, or external network destination was contacted.

## 5. Daemon file-error matrix (live CD)

`test_daemon_file_errors.py` ran against the accepted ISO over COM1. Each
case had to return a structured `HRPL err` body (or a documented B:
success), and the daemon had to answer a follow-up `ping` with `HRPL ok` /
`pong:1` / version `0.1.3`.

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
  `Unhandled Exception`, `Panic`, `Except:`, or debugger text.

## 6. Shots and checks

All 41 PNGs in this directory are 640x480, mode P, palette indices 0-15,
with 0 off-palette pixels:

- `PIL-CHECKS.txt`: `RESULT PASS shots=41`.
- `OCR-CHECKS.txt`: `RESULT PASS shots=41`; no `Except:`, `ERROR:`,
  `Undefined identifier`, `Fault:`, `Fatal`, `Unhandled Exception`, or
  `Panic` text.

No image was opened, previewed, or viewed in-model. All checks used PIL and
the in-repo 8x8 glyph OCR.

## 7. Notes

- `docs/research/daemon-file-errors.md` records the kernel/TinkerOS
  contracts, live-CD read-only semantics, existing guards, gaps, and the
  0.1.3 design.
- The ISO binary is gitignored and is not committed, released, or deployed.
- No sandbox commit, push, merge, tag, release, or branch delete was made.
  The work branch is `hermes/daemon-fix-0.1.3`; changes are uncommitted.
