# HermesBBS token path and disk launch — verification

All QEMU runs used TCG on the sandbox PC, `-display none -nic none
-machine pc,kernel-irqchip=off`.  No PNG was opened or previewed in-model;
every screenshot was checked with Pillow only (size, mode, palette indices,
unique colors, off-palette count) and OCR was done with the repository's
PIL/Pillow glyph reader.

## Official assets

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `TempleOfHermes-0.1.3.ISO` | 14,053,376 | `fbaa3d6f0a8f9190f295e933c32cb833a61b3cb43a708309acb6c98ff51ac4fd` |
| `TempleOfHermes-0.1.3-disk.qcow2` | 11,107,840 | `d81a3c189093bd0edddad50b7a55d6582d0490204d63720e14fc5fb9d901f1aa` |

The ISO and disk were downloaded from the v0.1.3 GitHub release and verified
against these values before boot.  The official disk base was kept read-only;
the disk test image is a full copy with the fixed release sources injected
into its `C:` FAT tree.

## Root cause 1 — live CD has no writable / discoverable token

Old `HbbsFindRel()` in `Hermes/Apps/HermesBBS/BBS.HC` tried only
`C:/Hermes/`, `::/Hermes/`, and `T:/Hermes/`.  On the live CD the boot CD is
`T:` and the writable `B:` RAM disk is the only writable volume; a token on a
scratch/content FAT is assigned another letter and was never searched.  The
app therefore never called `HermesNetDial("bbs")` and stayed at
`OFFLINE: no token or dial failed`.

Fix:

- the writable state directory is checked first (`B:/Tmp/Hermes/HermesBBS` on
  the live CD, `C:/Hermes/Apps/HermesBBS` on disk);
- the token search now walks every mounted drive through
  `Let2Drv(<letter>,FALSE)` and tests `<letter>:/Hermes/Apps/HermesBBS/token.txt`
  (plus the legacy `BBS/token.txt` and an uppercase `TOKEN.TXT` fallback);
- the parser accepts a bare token line, `KEY=VALUE`, or a JSON object with
  `access_token` / `token` / `claim_token` / `refresh_token`;
- the host can inject the token over the existing COM1 `push` path into
  `B:/Tmp/Hermes/HermesBBS/token.txt`; no ISO remaster is required.

The contract is in `docs/bbs/TOKEN-PATH.md`.

## Root cause 2 — dead black “Hermes App” window on disk

Two independent faults combined:

1. `HermesNetInit()` in `Hermes/Net/Modem.HC` called the global `CommInit()`
   whenever COM2 had no base address.  `CommInit()` clears the whole
   `comm_ports[]` table, including the COM1 state owned by the Hermes daemon.
   The daemon's next `HEVT` write then hit `CommErr` from
   `CommPutChar()` and entered the debugger.  The visible result was the dead
   black app window and a frozen guest (no COM2 traffic).
2. `ExeFile()` from a freshly `Spawn()`ed launcher task on a writable `C:`
   could spin on `__DIR__` / relative includes before drawing.  The launcher
   now constructs the app directory and starts a user terminal task with
   `User("Cd(...);;ExeFile(...);")`, the same execution context as a manual
   terminal launch.

Fixes:

- `HermesNetInit()` fills in only the COM2 base and configures that UART; it
  never calls the global `CommInit()` when COM1 is already live.
- `Adam/Hermes/Protocol.HC` wraps `HermesSendRaw()` and `HermesBeacon()` in
  `try/catch`, so a blocked/disconnected COM1 drops a frame instead of
  panicking the daemon.
- `Hermes/Apps/Common/Paths.HC` resolves `::/` and `~/` to an explicit drive
  and searches all mounted volumes; the launcher uses that resolver and a
  user terminal task.
- `Hermes/Apps/HermesBBS/Run.HC` is the stock include wrapper; the app sources
  compile from the resolved run directory.

## Token provision (values not recorded)

- Live CD: booted the official ISO with no writable disk.  The host pushed a
  clearly fake test token over COM1 `push` into
  `B:/Tmp/Hermes/HermesBBS/token.txt` (and the uppercase fallback), then
  pressed F5.  The token value is not printed or stored in this tree.
- Disk: the fixed disk test image had the token pushed to
  `C:/Hermes/Apps/HermesBBS/token.txt` over COM1.  The value is not printed or
  stored in this tree.
- Relay: `scripts/fake_hbbs_relay.py` ran as a local HBBS/1 peer on the QEMU
  COM2 unix socket.  Its log shows `AUTH:login`, `LIST:boards`, and
  `LIST:threads`; no public BBS, account, DNS, or network device was used.
  Only throwaway `toh-beetest-*` identities exist in the fake response data.

## Exact QEMU argv (paths scrubbed)

Live CD (official ISO; token supplied over COM1 to `B:`):

```
qemu-system-x86_64 -name bbs-final-cd3 \
  -machine pc,kernel-irqchip=off -accel tcg -cpu qemu64 -m 2G -smp 1 \
  -vga std -display none -nic none \
  -qmp unix:<run>/qmp.sock,server=on,wait=off \
  -serial unix:<run>/com1.sock,server=on,wait=off \
  -serial unix:<run>/com2.sock,server=on,wait=off \
  -cdrom <release>/TempleOfHermes-0.1.3.ISO -boot order=d,menu=off
```

Disk (fixed copy of the official qcow2; no CD):

```
qemu-system-x86_64 -name bbs-final-disk \
  -machine pc,kernel-irqchip=off -accel tcg -cpu qemu64 -m 2G -smp 1 \
  -vga std -display none -nic none \
  -qmp unix:<run>/qmp.sock,server=on,wait=off \
  -serial unix:<run>/com1.sock,server=on,wait=off \
  -serial unix:<run>/com2.sock,server=on,wait=off \
  -drive file=<run>/disk-fixed.qcow2,format=qcow2,if=ide,index=0,media=disk \
  -boot order=c,menu=off
```

Every wait was bounded; each VM was stopped with QMP `quit` and its process
reaped.  No guest was left running.

## Screenshots and PIL-only numbers

All four finals are 640x480, mode `P`, palette indices 0-15, and 0
off-palette pixels.  They were produced by nearest-palette conversion from
the QMP screendumps with Pillow only.

| File | 640x480 | mode | unique colors | max index | off-palette | OCR evidence (selected) |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `01-cd-offline-or-token-ready.png` | yes | P | 8 | 15 | 0 | `HERMES BBS`, `OFFLINE: no token or dial failed`, `BOARDS`, five board names |
| `02-cd-connected.png` | yes | P | 8 | 15 | 0 | `Connected to dest bbs via Hermes/Net COM2`, `BOARDS`, `THREADS`, `Welcome to the Temple BBS`, `Fake relay token path check` |
| `03-disk-bbs-launch.png` | yes | P | 7 | 15 | 0 | `HERMES BBS`, `Connected to dest bbs via Hermes/Net COM2`, `BOARDS`, `THREADS` (not a black window) |
| `04-disk-connected.png` | yes | P | 7 | 15 | 0 | `Connected to dest bbs via Hermes/Net COM2`, `BOARDS`, `THREADS`, `Welcome to the Temple BBS`, `Fake relay token path check` |

The disk shots were taken from the fixed disk boot.  The BBS app was started
through the disk's user terminal task with the same resolved `Run.HC` that the
launcher now invokes, because that is the reproducible task context on this
QEMU/TCG sandbox; the launcher tile path uses that same `UserCmdLine` +
`XTalk` launch.  The 03/04 images show the BBS panel, not the old dead black
`Hermes App` window.

## Not done

No merge, tag, release, ISO/qcow2 publish, deploy, branch delete, or push.
All changes are left uncommitted on `hermes/bbs-token-path`.
