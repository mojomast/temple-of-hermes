# TempleOfHermes-0.1.0 verification

- ISO: `dist/TempleOfHermes-0.1.0.ISO`
- Size: 14,020,608 bytes
- SHA256: `83bc2bba8d4c65c4884e3c8d6b4239e09cdcf5eafdba1bcf47392ab3b941f79d`
- ISO9660 volume id: `THE_TEMPLE_OF_HERMES`
- Built by: guest `Adam/Hermes/MakeDistro.HC` -> `BootDVDIns` -> `RedSeaISO`
  after the FAT32 overlay `D:/RUN.HC` copied 248 files to `C:`. No xorriso or
  stock-ISO remaster was used.
- Guest check: `Dir("T:/Hermes")` listed the six top-level entries (Apps, Art,
  Lore, Net, README.md, Registry.HC); every Run.HC above was opened from `T:`.
- Stock CD sha256:
  `feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4`

## Shots

All files in this directory are 640x480, mode P, palette indices 0-15, and
0 off-palette pixels (see `PIL-CHECKS.txt`). They were produced from QMP
screendumps and checked only with Python/PIL; no image was opened in-model.

- `01-boot-splash.png` - TinkerOS boot screen from the built disc
- `02-home-launcher.png` - autostarted home launcher, 18/18 icons loaded
- `03-app-hermes-chat.png` - Hermes Chat title, COM2 status, official icon
- `04-app-worldsim.png`, `05-app-codex.png`, `06-app-psyche.png`,
  `07-app-capybara.png`, `08-app-messenger.png`, `10-app-threshold.png`,
  `11-app-dojo.png`, `12-app-offerings.png`, `13-app-southpaw.png` - first
  app screen (Southpaw shows its official plate/header)
- `09-app-bbs.png` - BBS compile output and return to the shell (launch
  failure documented below)
- `14-app-modem-net.png` - Modem / Net status screen
- `19-net-echo.png` - COM2 local stub echo, `ECHO OK`; raw bytes in
  `net-echo.log`
- `20-shell.png` - usable `T:/Hermes/Apps>` HolyC prompt
- `15-game-caduceus.png`, `16-game-token-rain.png`, `17-game-spoon.png`,
  `18-game-dojo-duel.png` - first screen or the captured runtime error

## Compile / launch issues

- Boot warning (non-fatal): `OptPass3 ... WARNING: Using 64-bit reg var.`
  for `'ch' in 'HermesHandleLine'`.
- BBS: `HbbsInit` calls `DirMk("::/Hermes/Apps/HermesBBS")` before its try
  block. On the read-only live ISO the spawned UI task exits without drawing.
  The shot shows the successful compile and return to `T:/Hermes/Apps>`.
- Caduceus and Spoon: run-time `Except:Drv`/`DirMk` on the read-only ISO (the live disc has no
  writable `C:`; the games hardcode `C:/Tmp`); the
  shots capture the panic/register screen.
- Token Rain: `Except:Drv` on the read-only ISO (no writable `C:/Tmp`).
- Dojo Duel: `Except:Drv` from the `C:/Tmp` save-file path on the read-only ISO.
- Dojo (the separate app) did launch; its shot is the first scoreboard screen.

## Boot reliability

The built disc boots to the autostarted launcher on successful runs (shot 02).
Some boots stop during the late startup and never draw the launcher; retrying
the boot produced the shots above. This looks like an existing daemon/startup
race, not an ISO layout problem: the same disc immediately reaches the
launcher on the next boot. Keep this as a known issue for 0.1.0.
