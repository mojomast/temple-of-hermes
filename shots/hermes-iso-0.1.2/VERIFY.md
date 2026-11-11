# TempleOfHermes-0.1.2 verification

- ISO: `dist/TempleOfHermes-0.1.2.ISO`
- Size: 14,030,848 bytes
- SHA256: `9afc98ed2bb15a3ff26ebaca12ea392079292df6667b3c1c527fdd30d80cdb13`
- ISO9660 volume id: `THE_TEMPLE_OF_HERMES`
- Source: `hermes/iso-0.1.2` packed at
  `190501f12f13244e5d4cbd259d2cffaac1d74e03`; work branch created with
  `git checkout -B hermes/iso-0.1.2 HEAD` and left at that packed HEAD.
- Built by: guest `Adam/Hermes/MakeDistro.HC` -> `BootDVDIns` -> `RedSeaISO`
  after the FAT32 overlay `D:/RUN.HC` copied the Hermes tree to `C:`.
  No xorriso and no stock-ISO remaster were used.
- Base CD: TinkerOS 5.20-rc10, sha256
  `feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4`.
- All live-CD checks used QEMU TCG, `-display none -nic none
  -machine pc,kernel-irqchip=off`. The boot/app matrix used no writable guest
  disk. The COM1 plugin handshake used the plugin's own writable qcow2 shape.

This run rebuilt the ISO from the packed tree because no reusable artifact
with an accepted SHA-256 was present. In-guest ISO writing is not
bit-for-bit deterministic: size and volume id match the accepted artifact
shape, and this build's acceptance passed below.

## Boot reliability and overlay clear

20 independent boots, each a new VM with no disk, waiting up to 75 s for the
launcher and the HRPC `windows` list:

- **20/20 launcher passes** (target 20/20).
- Median launcher time: 11.8 s (range 11.7-11.9 s).
- A pass requires only the `Hermes Apps` window to be visible: no
  AutoComplete / System Keys guide, no Tour/Install terminal, and no other
  window overlapping the icon grid.
- Trial log: `boot-trials.log`; structured data: `boot-trials.json`.

Overlay clear result:
- `D:/RUN.HC` copied **254 files** onto `C:` and printed `OVERLAY DONE`.
- Each overlaid destination's compressed `.Z` twin was deleted by the same
  `RUN.HC` pass, so the boot path loads the patched 0.1.2 HolyC/DolDoc/art,
  not a stale compressed twin.
- The rebuilt ISO then booted to the 0.1.2 launcher with only the
  `Hermes Apps` window visible on all 20 trials.

## Home screen

- `02-home-launcher.png`: full-screen borderless launcher, 18 entries in a
  6x3 grid, unique key hints, one ASCII footer help line.
- `01-boot-splash.png`: the built disc boot screen / Nous Girl splash.

## App launch matrix

Every entry was driven from the home screen with a real mouse click and with
its shortcut key. `return` means the clean, focused `Hermes Apps` launcher
was visible again with no overlapping window. `diff` is the sampled pixel
difference from the pre-launch home shot.

| App | Click | Key | Return (click/key) | Click diff | Key diff | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Temple | PASS | PASS | clean launcher / clean launcher | 0.00 | 0.00 | `app-temple-click.png`, `app-temple-key.png`, `temple-check.json` |
| Hermes Chat | PASS | PASS | PASS/PASS | 0.96 | 0.96 | `app-hermes-chat-*.png`, `return-hermes-chat-*.png` |
| WorldSim | PASS | PASS | PASS/PASS | 0.84 | 0.84 | `app-worldsim-*.png`, `return-worldsim-*.png` |
| Codex | PASS | PASS | PASS/PASS | 0.92 | 0.92 | `app-codex-*.png`, `return-codex-*.png` |
| Psyche | PASS | PASS | PASS/PASS | 0.97 | 0.97 | `app-psyche-*.png`, `return-psyche-*.png` |
| Capybara | PASS | PASS | PASS/PASS | 0.93 | 0.93 | `app-capybara-*.png`, `return-capybara-*.png` |
| Messenger | PASS | PASS | PASS/PASS | 0.25 | 0.25 | `app-messenger-*.png`, `return-messenger-*.png` |
| BBS | PASS | PASS | PASS/PASS | 0.14 | 0.13 | `app-bbs-*.png`, `return-bbs-*.png` |
| Threshold | PASS | PASS | PASS/PASS | 0.18 | 0.18 | `app-threshold-*.png`, `return-threshold-*.png` |
| Dojo | PASS | PASS | PASS/PASS | 0.82 | 0.82 | `app-dojo-*.png`, `return-dojo-*.png` |
| Offerings | PASS | PASS | PASS/PASS | 0.84 | 0.84 | `app-offerings-*.png`, `return-offerings-*.png` |
| Southpaw | PASS | PASS | PASS/PASS | 0.84 | 0.84 | `app-southpaw-*.png`, `return-southpaw-*.png` |
| Modem / Net | PASS | PASS | PASS/PASS | 0.97 | 0.97 | `app-modem-net-*.png`, `return-modem-net-*.png` |
| Caduceus | PASS | PASS | PASS/PASS | 0.76 | 0.76 | `app-caduceus-*.png`, `return-caduceus-*.png` |
| Token Rain | PASS | PASS | PASS/PASS | 0.25 | 0.25 | `app-token-rain-*.png`, `return-token-rain-*.png` |
| Spoon | PASS | PASS | PASS/PASS | 0.30 | 0.30 | `app-spoon-*.png`, `return-spoon-*.png` |
| Dojo Duel | PASS | PASS | PASS/PASS | 0.16 | 0.16 | `app-dojo-duel-*.png`, `return-dojo-duel-*.png` |
| About | PASS | PASS | PASS/PASS | 0.97 | 0.97 | `app-about-*.png`, `return-about-*.png` |

**All 18 launcher entries passed.** The 17 non-Temple entries (including
About) launched from both a mouse click and a key and returned to the
launcher. Temple stays on the home screen by design; click and `T` both left
the clean launcher visible with no overlapping window. About opened the
About/help view.

## COM2 echo

`net-echo.log` records the local unix-socket stub transcript. The guest sent
`HERMES-NET-ECHO-01` (18 bytes) and the stub echoed it, followed by `ECHO OK`
on screen in `19-net-echo.png`. COM1 stayed the Hermes HRPC console. No BBS,
VPS, public host, or external network destination was contacted.

## COM1 plugin serial handshake (D)

- Plugin source: `mojomast/hermes-templeos` at
  `b15c396c308b638c00959740dfa3d28920f45484` (cloned read-only; not modified,
  committed, or pushed).
- Boot shape: the plugin's own `templeos.qemu.build_argv` (TCG,
  `-machine pc,kernel-irqchip=off`, `-display none`, `-nic none`, QMP/VNC and
  COM1 on unix sockets) with this ISO supplied as the custom ISO path.
- COM1 path: the plugin's `templeos.serial.SerialPort` stayed open for the
  session. The plugin's own `templeos_screen` `read_text` path returned the
  beacon with `source: serial`.
- Beacon received: `HBEACON TempleOfHermes/0.1.0`.
- Successful daemon call through that COM1 path:
  `HREQ 1 ping 0` -> `HRPL 1 ok 54`
  `{"pong":1,"t": 10.213,"mode":"user","version":"0.1.0"}`.
- Evidence: `com1-handshake.log`, `com1-handshake.json`,
  `com1_plugin_handshake.py`.
- The in-guest daemon and status strings still report version `0.1.0`
  (`HBEACON`, ping payload). That is expected for this 0.1.2 tree and is
  recorded here, not treated as a failure.

## Shell

`20-shell.png` is a usable HolyC shell opened in a new visible user task;
`7*7;` returned `ans=0x00000031=49` and `Dir("T:/Hermes/Apps")` listed the
app tree.

## Shots and checks

All PNGs in this directory are 640x480, mode P, palette indices 0-15, with
0 off-palette pixels: `PIL-CHECKS.txt` reports `RESULT PASS shots=74`.
`OCR-CHECKS.txt` reports `RESULT PASS shots=74` after a text-only scan for
exception strings. No image was opened, previewed, or viewed in-model; all
checks used PIL and the in-repo 8x8 glyph OCR.

## Notes

- The launcher hides no app behind another window and restores itself when
  the app task exits (Esc / app quit), including popup-based apps.
- `MakeDistro.HC` was not edited.
- The ISO binary is gitignored and is not committed, released, or deployed.
- No branch was merged, tagged, or pushed. No sandbox commit was made.
