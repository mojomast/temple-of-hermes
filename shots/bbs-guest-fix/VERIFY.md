# Hermes BBS guest fix — 0.1.4-test2 verification

Work branch: `hermes/bbs-token-path`, packed from
`5e2e4614e94f1810049092ae71a02ceafdfd60a9`.  All Temple of Hermes changes are
left **uncommitted**.  No merge, tag, push, publish, or deploy was done.

Environment: Ubuntu 24.04 sandbox PC, QEMU 8.2.2, all TCG.  Every run used
`-display none -nic none -machine pc,kernel-irqchip=off -vga std`.  No PNG was
opened, previewed, or read visually; screenshots were handled only by Pillow.

## Assets

The sealed test images were not present in this sandbox, so the fix images were
rebuilt from the uncommitted tree through the repository's own pipelines:

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| sealed `TempleOfHermes-0.1.4-test.ISO` (reference) | 14051328 | `2d8cc40aa17251696ebfb45d6c08da511b00e68f9993c756de0fcb64d589f50f` |
| sealed `TempleOfHermes-0.1.4-test-disk.qcow2` (reference) | 11100160 | `62525e74950991096dc6889cdca91f3deb88022e9e4cc0d325026d4ced0c5101` |
| rebuilt `TempleOfHermes-0.1.4-test2.ISO` | 14075904 | `9173395a44a45cb364945575cac2490ee18a6d939db0c83a16b1bee70db6f446` |
| rebuilt preinstalled disk from that ISO | 11110912 | `5e519a35e5534f6f3f928bced468f855284ad1de5eaf149aec6bd04d019e15c9` |

The rebuilt ISO came from `scripts/build_iso.py` /
`shots/hermes-integration/build_from_installed.py`; the disk came from
`scripts/build_disk_image.py` using that ISO.  No ISO or qcow2 binary was added
to git.

## Real wiring reproduced

Disk boot (the host wrapper is equivalent to the real host: the overlay disk is
IDE index 0 and the wrapper adds the read-only content CD at IDE index 3):

```
qemu-system-x86_64 -name <name>
  -machine pc,kernel-irqchip=off -accel tcg -cpu qemu64 -m 2G -smp 1
  -vga std -display none -nic none
  -qmp unix:<run>/qmp.sock,server=on,wait=off
  -vnc unix:<run>/vnc.sock
  -serial unix:<run>/com1.sock,server=on,wait=off
  -serial unix:<run>/modem.sock,server=on,wait=off
  -boot order=c,menu=on
  -drive file=<run>/TempleOfHermes-0.1.4-test2-disk.qcow2,format=qcow2,if=ide,index=0,media=disk
  -drive file=<content>/hermes-play.iso,media=cdrom,format=raw,if=ide,index=3,readonly=on
```

Live CD (plugin flags plus the wrapper-equivalent FAT at index 0, scratch qcow2
at index 1, and content CD at index 3):

```
qemu-system-x86_64 -name <name>
  -machine pc,kernel-irqchip=off -accel tcg -cpu qemu64 -m 2G -smp 1
  -vga std -display none -nic none
  -qmp unix:<run>/qmp.sock,server=on,wait=off
  -vnc unix:<run>/vnc.sock
  -serial unix:<run>/com1.sock,server=on,wait=off
  -serial unix:<run>/modem.sock,server=on,wait=off
  -cdrom <run>/TempleOfHermes-0.1.4-test2.ISO
  -boot order=d,menu=on
  -drive file=<run>/scratch.qcow2,format=qcow2,if=ide,index=1,media=disk
  -drive file=<run>/content.img,format=raw,if=ide,index=0,media=disk
  -drive file=<content>/hermes-play.iso,media=cdrom,format=raw,if=ide,index=3,readonly=on
```

A read-only ISO at index 3 is the important part for root cause 2.  It is
assigned a drive letter (T: in these runs), exactly as on the real host.

## Root cause 1 — COM1 TXFR push/list timeout

`templeos/files.py` v0.2.2 used the `TXFR` framed protocol on COM1 and waited
`DEFAULT_TIMEOUT_S=8.0` for `CMD_PUSH_OK`.  The Hermes daemon already owns COM1
and its `HermesDaemonTask` loop reads COM1 as `HREQ` text lines.  The daemon
therefore consumed the binary TXFR frame, no `TXFR` helper was running, and the
host never got a reply.  This is the same rule already written in
`docs/USING-WITH-HERMES-AGENTS.md`: do not load `Xfer.HC` while HRPC is running.

Evidence with the original v0.2.2 `files.py` on a booted disk guest
(`v022-evidence.json`):

- `templeos_files.list` returned
  `timed out waiting for a serial file-transfer frame` after **8.05 s**.
- `templeos_files.push` returned the same error after **8.05 s**.
- `stat` before the attempt: `C:/Hermes/Apps/HermesBBS/token.txt` `exists:0`.
- After the two TXFR attempts the daemon no longer answered an HRPC `stat`
  within 20 s; the TXFR bytes had also disturbed its line reader.

Fix (host patch, not a guest change): `templeos/files.py` now tries the
daemon's own HRPC operations first — id-matched `HREQ list/pull/push` over the
same open COM1 serial port, skipping `HBEACON`/`HEVT` frames — and falls back to
TXFR only when no daemon answers.  With the fixed file tool the token push
completes in **0.01–0.03 s**, returns `"via": "hrpc"`, and the daemon remains
alive and answerable.

Host patch: `/output/hermes-templeos.patch` (only `templeos/files.py`, based on
`0e3167ea8014e7187fdf86d2a4f973bc0f0d18ea`), plus a full copy at
`/output/hermes-templeos/templeos/files.py`.  Host unit tests:
`python3 -m pytest -q tests/test_files.py` — 15 passed.

The same fixed host module was also exercised for all three operations against
a live guest: `list` returned `via:"hrpc"` with five directory entries,
`push` returned `via:"hrpc"` `ok:true`, and `pull` returned `via:"hrpc"`
`ok:true` with the 20-byte fake token.

## Root cause 2 — disk S-key black window with no COM2 traffic

`HbbsLoadToken()` checked the writable state directory (pass), then
`HbbsFindRel()` scanned every drive letter.  On disk boot the host wrapper's
read-only content ISO is attached at IDE index 3 and appears as `T:`.  The scan
called `IsFile("T:/Hermes/Apps/HermesBBS/token.txt")` on that non-boot ISO9660
volume and blocked inside ISO9660 lookup, before the first UI draw.  The window
was already created, so it stayed empty; `HbbsUiRefresh()` never ran and COM2
never saw a byte.

Evidence from a temporary breadcrumb build (see `disk-hang-breadcrumbs.txt`):
the state-directory and `::/` / `~/` checks completed, the loop wrote drive
markers for `B:`, `C:`, and `T:`, then stopped before the post-loop marker.
Task title was `HermesBBSUI;.`, focused text was empty, and COM2 bytes were 0.

Fix (guest):

- `Hermes/Apps/HermesBBS/BBS.HC` `HbbsFindRel()` now scans only **writable**
  volumes.  The boot volume is still covered by the direct `::/` and `~/`
  checks; a host-injected scratch FAT is writable and still found.
- `HbbsUiTask()` draws one frame before the token search / dial, so a future
  slow probe cannot leave a blank black window.

After the fix, a disk boot with **no token** draws
`OFFLINE: no token or dial failed` and the board panel immediately, instead of
hanging (`disk-no-token-after-fix.ocr.txt`).  With a token it reaches Connected.

## Relay and endpoint

The COM2 relay used the real repository `host/hermes_modem.py` with
`HermesModem(enabled=True, allow_list=("bbs",))`, connected as a unix client to
the QEMU `modem.sock` serial.  Its transport was a TLS client to a local
loopback HBBS/1 endpoint (self-signed test certificate, verification disabled
for the test).  The public community endpoint was not reachable from this
sandbox, so the loopback TLS endpoint supplied the Connected proof; the only
allowed destination name was still `bbs`.

The relay and TLS endpoint log command names and byte counts only, never
payloads or token values.  The test token is the clearly fake
`test-token-not-real`; no account, claim, access, refresh, or session token was
recorded.

Observed disk modem sequence (names/counts only):

```
ATZ
ATD bbs -> DIAL dest=bbs result=connect
AT+SEND 22 -> OK 22
AT+SEND 80 -> OK 80
AT+RECV 4096 -> 331 bytes
...
ATH
```

The TLS endpoint logged `AUTH:login`, `LIST:boards`, and `LIST:threads`.

## Token delivery and Connected proof

Both boots used the fixed file tool, which is the real plugin push path's
successor: HRPC `push` on the already-open COM1.

Disk (preinstalled disk rebuilt from the fixed ISO):

- `push` to `C:/Hermes/Apps/HermesBBS/token.txt`: `ok`, `via: hrpc`, 20 bytes,
  0.01 s.
- Pressed `S`; the launcher opened the BBS window and reached
  `Connected to dest bbs via Hermes/Net COM2` after two polls.

Live CD (fixed ISO plus wrapper-equivalent extra drives):

- Created/confirmed `B:` RAM state dirs through the daemon, then `push` to
  `B:/Tmp/Hermes/HermesBBS/token.txt`: `ok`, `via: hrpc`, 20 bytes, 0.01 s.
- Pressed `S`; the BBS window reached
  `Connected to dest bbs via Hermes/Net COM2` after two polls.

Selected OCR text (from the fixed runs):

Disk:
`HERMES BBS  dest bbs  HBBS/1  HERMES/NET COM2`
`Connected to dest bbs via Hermes/Net COM2`
`BOARDS`, `THREADS`, `Loopback TLS check`, `by Loopback [untrusted]`

Live CD:
`HERMES BBS  dest bbs  HBBS/1  HERMES/NET COM2`
`Connected to dest bbs via Hermes/Net COM2`
`BOARDS`, `THREADS`, `Loopback TLS check`, `by Loopback [untrusted]`

No `OFFLINE`, `no token`, or `dial failed` appears in either final OCR file.

## Screenshots (Pillow-only checks)

| File | Size | Mode | Unique indices | Max index | Off-palette | OCR status |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `01-disk-s-connected.png` | 640x480 | P | 7 | 6 | 0 | Connected |
| `02-cd-s-connected.png` | 640x480 | P | 8 | 7 | 0 | Connected |

Both are nearest-quantized to 16 colours with Pillow (`quantize`, no dither);
all pixel indices are in 0–15 and there are zero off-palette pixels.  OCR text
is saved in the matching `.ocr.txt` files.  No PNG was viewed in-model.

## Files changed in this repository

- `Hermes/Apps/HermesBBS/BBS.HC` — writable-only drive scan; first draw before
  token/dial.
- `docs/bbs/TOKEN-PATH.md` — HRPC-first host push, TXFR warning, writable-only
  scan, disk-boot ISO note.
- `shots/bbs-guest-fix/` — this verification, final shots, OCR, relay/modem/TLS
  logs, v0.2.2 timeout evidence, and the small test harness.
- Host patch (outside this repo, written under `/output/`):
  `templeos/files.py` only.

No other host files were changed.  No ISO/qcow2 was committed; QEMU is stopped.
