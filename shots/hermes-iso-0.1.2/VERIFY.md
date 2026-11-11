# TempleOfHermes-0.1.2 verification

- ISO: `dist/TempleOfHermes-0.1.2.ISO`
- Size: 14,030,848 bytes
- SHA256: `8bcf43c31689e328716ca42f0255f1ede834dd39cd0fa345bc96719d60f74c60`
- ISO9660 volume id: `THE_TEMPLE_OF_HERMES`
- Built by: guest `Adam/Hermes/MakeDistro.HC` -> `BootDVDIns` -> `RedSeaISO`
  after the FAT32 overlay `D:/RUN.HC` copied the Hermes tree to `C:`.
  No xorriso or stock-ISO remaster was used.
- Base: `hermes/iso-0.1.1` at
  `2ee750e9205809c405aa5494cdfe8d49b35a07d5`; work branch
  `hermes/iso-0.1.2`, uncommitted worktree.
- Stock CD sha256:
  `feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4`
- All tests are live-CD only: QEMU TCG, `-display none -nic none
  -machine pc,kernel-irqchip=off`, no writable guest disk.

## Boot reliability and overlay clear

20 independent boots, each a new VM with no disk, waiting up to 75 s for
the launcher and the HRPC `windows` list:
- **20/20 launcher passes** (target 20/20; acceptance threshold 19/20).
- A pass requires only the `Hermes Apps` window to be visible: no
  AutoComplete/System Keys guide, no Tour/Install terminal, and no other
  window overlapping the icon grid.
- Trial log: `boot-trials.log`; structured data: `boot-trials.json`.
- Median observed launcher time: about 11.6 s.

## Home screen

- `02-home-launcher.png`: full-screen borderless launcher, 18 entries in a
  6x3 grid, unique key hints, one clean ASCII footer help line.
- `01-boot-splash.png`: the built disc boot screen / Nous Girl splash.

## App launch matrix

| App | Mouse click | Key | Return to launcher | Shot evidence |
| --- | --- | --- | --- | --- |
| Hermes Chat | PASS | PASS | PASS/PASS | `app-hermes-chat-click.png`, `app-hermes-chat-key.png`, `return-hermes-chat-*.png` |
| WorldSim | PASS | PASS | PASS/PASS | `app-worldsim-click.png`, `app-worldsim-key.png`, `return-worldsim-*.png` |
| Codex | PASS | PASS | PASS/PASS | `app-codex-click.png`, `app-codex-key.png`, `return-codex-*.png` |
| Psyche | PASS | PASS | PASS/PASS | `app-psyche-click.png`, `app-psyche-key.png`, `return-psyche-*.png` |
| Capybara | PASS | PASS | PASS/PASS | `app-capybara-click.png`, `app-capybara-key.png`, `return-capybara-*.png` |
| Messenger | PASS | PASS | PASS/PASS | `app-messenger-click.png`, `app-messenger-key.png`, `return-messenger-*.png` |
| BBS | PASS | PASS | PASS/PASS | `app-bbs-click.png`, `app-bbs-key.png`, `return-bbs-*.png` |
| Threshold | PASS | PASS | PASS/PASS | `app-threshold-click.png`, `app-threshold-key.png`, `return-threshold-*.png` |
| Dojo | PASS | PASS | PASS/PASS | `app-dojo-click.png`, `app-dojo-key.png`, `return-dojo-*.png` |
| Offerings | PASS | PASS | PASS/PASS | `app-offerings-click.png`, `app-offerings-key.png`, `return-offerings-*.png` |
| Southpaw | PASS | PASS | PASS/PASS | `app-southpaw-click.png`, `app-southpaw-key.png`, `return-southpaw-*.png` |
| Modem / Net | PASS | PASS | PASS/PASS | `app-modem-net-click.png`, `app-modem-net-key.png`, `return-modem-net-*.png` |
| Caduceus | PASS | PASS | PASS/PASS | `app-caduceus-click.png`, `app-caduceus-key.png`, `return-caduceus-*.png` |
| Token Rain | PASS | PASS | PASS/PASS | `app-token-rain-click.png`, `app-token-rain-key.png`, `return-token-rain-*.png` |
| Spoon | PASS | PASS | PASS/PASS | `app-spoon-click.png`, `app-spoon-key.png`, `return-spoon-*.png` |
| Dojo Duel | PASS | PASS | PASS/PASS | `app-dojo-duel-click.png`, `app-dojo-duel-key.png`, `return-dojo-duel-*.png` |
| About | PASS | PASS | PASS/PASS | `app-about-click.png`, `app-about-key.png`, `return-about-*.png` |

**17/17 apps passed both a real home-screen mouse click and a
shortcut key, with the launcher back visible and focused afterwards.**
Temple stays on the home screen by design; About opens the About/help page
and returns (F1 also opens it).

## COM2 echo

`net-echo.log` records the local unix-socket stub transcript. The guest sent
`HERMES-NET-ECHO-01` (18 bytes) and received the stub echo (18 bytes), then
`ECHO OK` appeared on screen in `19-net-echo.png`. COM1 was left to HRPC; no
BBS, VPS, or external network destination was contacted.

## Shell

`20-shell.png` is a usable HolyC shell opened in a new visible user task;
`7*7;` returned `ans=0x00000031=49` and `Dir("T:/Hermes/Apps")` listed the
app tree.

## Shots and checks

All files in this directory are 640x480, mode P, palette indices 0-15, and
0 off-palette pixels (see `PIL-CHECKS.txt`). `OCR-CHECKS.txt` records a
text-only scan of every shot for exception strings. No image was opened or
viewed in-model; all checks use PIL and the in-repo 8x8 glyph OCR.

## Notes

- The launcher hides no app behind another window and restores itself when
  the app task exits (Esc / app quit), including popup-based apps.
- `Psyche` is a small text signal-field view so the live disc stays
  responsive under TCG; the other games keep their 16-colour art.
- `MakeDistro.HC` was not edited.
- The ISO binary is gitignored and is not committed, released, or deployed.
