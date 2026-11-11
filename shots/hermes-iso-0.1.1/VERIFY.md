# TempleOfHermes-0.1.1 verification

- ISO: `dist/TempleOfHermes-0.1.1.ISO`
- Size: 14,026,752 bytes
- SHA256: `70ded88b90de9ff2f5fe43de562e99aeac2e329aa73b03a8eccbad4f07a1110f`
- ISO9660 volume id: `THE_TEMPLE_OF_HERMES`
- Built by: guest `Adam/Hermes/MakeDistro.HC` -> `BootDVDIns` -> `RedSeaISO`
  after the FAT32 overlay `D:/RUN.HC` copied 249 files to `C:`. No xorriso or
  stock-ISO remaster was used.
- Base: `hermes/iso-0.1` at
  `99d5e88159f5cb2193c03c429bc0474bfff7f203`; work branch
  `hermes/iso-0.1.1`, uncommitted worktree.
- Stock CD sha256:
  `feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4`
- All tests are live-CD only: QEMU TCG, `-display none -nic none
  -machine pc,kernel-irqchip=off`, no writable guest disk.

## Boot reliability

20 independent boots, each a new VM with no disk, waiting up to 75 s for
`Art icons` / `Click an icon`:

- **20/20 launcher passes** (target 20/20; acceptance threshold 19/20).
- Trial log: `boot-trials.log`; structured data: `boot-trials.json`.
- Median observed launcher time: about 12.3 s.

## Shots

All files in this directory are 640x480, mode P, palette indices 0-15, and
0 off-palette pixels (see `PIL-CHECKS.txt`). They were produced from QMP
screendumps and checked only with Python/PIL; no image was opened in-model.
`OCR-CHECKS.txt` records a text-only scan of every shot for exception strings.

| Shot | Result |
| --- | --- |
| `01-boot-splash.png` | PASS: TinkerOS boot screen from the built disc |
| `02-home-launcher.png` | PASS: autostarted Hermes home launcher |
| `03-app-hermes-chat.png` | PASS: Hermes Chat first screen |
| `04-app-worldsim.png` | PASS: WorldSim |
| `05-app-codex.png` | PASS: Codex |
| `06-app-psyche.png` | PASS: Psyche |
| `07-app-capybara.png` | PASS: Capybara |
| `08-app-messenger.png` | PASS: Messenger |
| `09-app-bbs.png` | PASS: Hermes BBS UI draws offline boards/threads, no token dial |
| `10-app-threshold.png` | PASS: Threshold |
| `11-app-dojo.png` | PASS: Dojo |
| `12-app-offerings.png` | PASS: Offerings |
| `13-app-southpaw.png` | PASS: Southpaw |
| `14-app-modem-net.png` | PASS: Modem / Net status on COM2 |
| `15-game-caduceus.png` | PASS: Caduceus first screen |
| `16-game-token-rain.png` | PASS: Token Rain first screen |
| `17-game-spoon.png` | PASS: Spoon first screen |
| `18-game-dojo-duel.png` | PASS: Dojo Duel first screen |
| `19-net-echo.png` | PASS: COM2 local-stub echo, `ECHO OK` |
| `20-shell.png` | PASS: usable `T:/Hermes/Apps>` HolyC shell |

The five 0.1.0 read-only failures now present UI without `Except:Drv`:
BBS, Caduceus, Token Rain, Spoon, and Dojo Duel.

## COM2 echo

`net-echo.log` records the local unix-socket stub transcript. The guest sent
`HERMES-NET-ECHO-01` (18 bytes) and received the stub echo (18 bytes), then
`ECHO OK` appeared on screen in `19-net-echo.png`. COM1 was left to HRPC; no
BBS, VPS, or external network destination was contacted.

## Notes

- `StateDir.HC` resolves `C:/Tmp` on a writable install and
  `B:/Tmp/Hermes/<App>` on the read-only live CD. If no writable folder can
  be created, the apps continue without saving state.
- BBS creates a terminal document in its spawned UI task, marks the window
  visible, and raises it to the top; with no token it shows the offline boards
  rather than throwing.
- Non-fatal compiler warnings from the guest (`WARNING: Unused var`,
  `WARNING: Using 64-bit reg var.`) do not stop any app or game.
- `MakeDistro.HC` was not edited.
