# HermesBBS token freshness and error-code status — verification

Work branch: `hermes/bbs-token-path`, packed from
`9d7d3ec4a43890855cdb9eaab656f32fd63cb325`.  All Temple of Hermes changes are
left **uncommitted**.  No merge, tag, push, publish, deploy, or branch switch
was done.  This is a test-build fix, not a release.

Environment: Ubuntu 24.04 sandbox PC, QEMU 8.2.2, all TCG.  Every run used
`-display none -nic none -machine pc,kernel-irqchip=off -vga std`.  No PNG was
opened, previewed, or read visually in-model.  Pillow was used only for size,
mode, palette-index, unique-colour, and off-palette checks, plus the
repository's PIL glyph reader for OCR text.

## Root cause

1. **Token freshness.**  HBBS/1 access tokens live about 15 minutes
   (`docs/bbs/HBBS-1.md`, transport table and section 5.1/5.3); refresh
   credentials last about 30 days.  The failed live injection preferred a
   host-side legacy `token.txt` in the plugin BBS data directory over the
   current agent credential JSON.  That legacy file was roughly 13.7 hours
   old and did not match the current JSON access or refresh credential.  The
   guest therefore sent a valid *login* frame carrying an expired access
   token.  The server's 124-byte reply is the documented `token_expired`
   envelope, not a framing error.
2. **Guest status hid the code.**  `HbbsSessionBegin()` mapped `no_token`,
   `dial_failed`, `auth_failed`, `bad_response_header`, and a parsed
   `ok:false` (including `token_expired`) to the single generic string
   `OFFLINE: no token or dial failed`.

The guest AUTH frame was already correct and is unchanged:

```json
{"v":1,"command":"AUTH","args":{"action":"login","token":"<access-token>"}}
```

There is no HBBS/1 `resume` action.

## Fix

Guest (`Hermes/Apps/HermesBBS/BBS.HC`):

- Added `HbbsErrorCode()`: it reads only the nested HBBS/1 `error.code`,
  copies a short machine-identifier charset, and ignores every other reply
  field.  No token, refresh credential, or message text is painted.
- `HbbsSessionBegin()` stores that code on `ok:false`; `HbbsFinish()` and
  `HbbsResultFromCall()` use it for non-session server failures too.
- `HbbsUiRefresh()` now prints `OFFLINE: <code>` (for example
  `OFFLINE: token_expired`).  Local failures show their own code such as
  `no_token` or `dial_failed`.

Host (`hermes-templeos` patch, only the assigned files):

- `templeos/session.py` adds `bbs_push_guest_token()`.  It loads the current
  agent JSON/creds pair (legacy `token.txt` excluded), refreshes immediately
  with the refresh credential, persists the rotated access/refresh pair, then
  writes the fresh access token to a mode-0600 temporary file and pushes it to
  the documented path.  Without a refresh credential it verifies the stored
  access token with AUTH login before pushing, so an expired token is never
  re-pushed.  The token never appears in the returned envelope.
- `templeos/bbs.py` `discover_credentials()` gained
  `include_token_txt=False`; the new helper uses it so a stale `token.txt`
  cannot win over current agent credentials.
- `templeos/files.py` keeps bytes read during an HRPC probe and hands them to
  the TXFR fallback, so the daemon probe cannot swallow a pending framed
  reply.  This also fixes the one baseline host-test failure at 57631e9.
- No fifth tool and no tool-schema change.  Exactly four tools remain.

Documented guest paths (the only paths the helper accepts):

```
C:/Hermes/Apps/HermesBBS/token.txt   (installed disk)
B:/Tmp/Hermes/HermesBBS/token.txt    (live CD RAM state directory)
```

Pushing the refresh credential for the guest to AUTH-refresh was not added:
refresh rotates and invalidates the previous credential, and a live-CD RAM
volume cannot persist the rotation back to the host store.  The host instead
refreshes first and pushes the fresh 15-minute access token.

## Evidence (no token values)

A local loopback TLS HBBS/1 peer returned the documented error envelope:

```json
{"v":1,"ok":false,"command":"AUTH","error":{"code":"token_expired","message":"access token expired"}}
```

The real COM2 relay was the repository's `host/hermes_modem.py` with
`enabled=True` and allow-list exactly `("bbs",)`.  TLS and modem logs contain
command names, byte counts, and denials only.  No AUTH payload or token value
is logged.

Disk boot (IDE index 0 overlay/disk plus read-only content CD at index 3):

- the injected current sources compiled in-guest;
- an old fixture token produced `OFFLINE: token_expired`;
- the host helper rotated a clearly fake fixture refresh credential, pushed a
  fresh fake access token to `C:/Hermes/Apps/HermesBBS/token.txt`, and F5
  reached `Connected to dest bbs via Hermes/Net COM2` with board and thread
  rows.

Live CD (plugin `-cdrom`, wrapper FAT at index 0, scratch qcow2 at index 1,
content CD at index 3):

- `MountAuto(TRUE)` mounted the wrapper FAT as `C:` (this v0.1.3 live CD did
  not auto-mount the extra ATA disk at boot);
- the same current sources ran from `C:`;
- a fixture token at `B:/Tmp/Hermes/HermesBBS/token.txt` produced
  `OFFLINE: token_expired`;
- after the host refresh+push of a fresh fake access token, F5 reached
  `Connected to dest bbs via Hermes/Net COM2` with the loopback board/thread
  rows.

The public community endpoint was not contacted from this sandbox.  The
loopback TLS endpoint is the task's allowed substitute for Connected proof;
the token-expired proof uses the exact documented envelope.

## QEMU wiring (paths scrubbed)

Disk:

```
qemu-system-x86_64 -name bbs-auth-disk
  -machine pc,kernel-irqchip=off -accel tcg -cpu qemu64 -m 2G -smp 1
  -vga std -display none -nic none
  -qmp unix:<run>/qmp.sock,server=on,wait=off
  -serial unix:<run>/com1.sock,server=on,wait=off
  -serial unix:<run>/com2.sock,server=on,wait=off
  -boot order=c,menu=on
  -drive file=<run>/disk.raw,format=raw,if=ide,index=0,media=disk
  -drive file=<assets>/TempleOfHermes-0.1.3.ISO,media=cdrom,format=raw,if=ide,index=3,readonly=on
```

Live CD:

```
qemu-system-x86_64 -name bbs-auth-live
  -machine pc,kernel-irqchip=off -accel tcg -cpu qemu64 -m 2G -smp 1
  -vga std -display none -nic none
  -qmp unix:<run>/qmp.sock,server=on,wait=off
  -serial unix:<run>/com1.sock,server=on,wait=off
  -serial unix:<run>/com2.sock,server=on,wait=off
  -cdrom <assets>/TempleOfHermes-0.1.3.ISO -boot order=d,menu=on
  -drive file=<run>/wrapper.img,format=raw,if=ide,index=0,media=disk
  -drive file=<run>/scratch.qcow2,format=qcow2,if=ide,index=1,media=disk
  -drive file=<assets>/TempleOfHermes-0.1.3.ISO,media=cdrom,format=raw,if=ide,index=3,readonly=on
```

Every wait was bounded.  Each VM was stopped with QMP `quit`; no guest was
left running.

## PIL-only screenshot results

All four finals are 640x480, mode `P`, palette indices present are 0-6,
maximum index 6, and zero off-palette pixels.

| File | Size | Mode | Unique | Max index | Off-palette | SHA-256 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `01-disk-token-expired.png` | 640x480 | P | 7 | 6 | 0 | `3f41d5c7b9a019e7ee94971df87bbcd197c20cf72d3cf75c41b2323b68c8ab0d` |
| `02-disk-connected.png` | 640x480 | P | 7 | 6 | 0 | `cce542f665b36f88cde20befbba6b9767dd77d71fa43ed9eee96884df969113e` |
| `03-live-token-expired.png` | 640x480 | P | 7 | 6 | 0 | `1aa52c328df5dbfaf1c696bdde04a4092d67c5c182ab1838ad0c1300f8a15e0c` |
| `04-live-connected.png` | 640x480 | P | 7 | 6 | 0 | `8d2c13c00c1ae2d6a6c3ab16575a4cea46a3d2b873ff32d1256e88849f6e88b3` |

OCR evidence: every image contains `HERMES BBS` and the board list.  The two
token-expired images contain `OFFLINE: token_expired`; the two connected
images contain `Connected to dest bbs via Hermes/Net COM2`,
`Fresh token accepted`, and `Token path check`.  Full OCR text is stored next
to each PNG.

## Hashes

| Artifact | SHA-256 |
| --- | --- |
| `Hermes/Apps/HermesBBS/BBS.HC` | `83f2bba6b68bafdca5b0e88c9803af2cc34732906e7674ae9b1b4b8bafa27f64` |
| `docs/bbs/TOKEN-PATH.md` | `7ce224e4eb572071dadfd0a52466fd0a69b4d2964381fd7852751ee8103d8579` |
| `Hermes/Apps/HermesBBS/README.md` | `2b2dbbb45bd84c9145ede752609b29b677cf87afea0317413e85213370700333` |
| `/output/hermes-templeos.patch` | `d42b7938dacf7eee367999276611620d17fee371f847f39a6c425ec4e80e3d1d` |
| base `TempleOfHermes-0.1.3.ISO` | `fbaa3d6f0a8f9190f295e933c32cb833a61b3cb43a708309acb6c98ff51ac4fd` |
| base `TempleOfHermes-0.1.3-disk.qcow2` | `d81a3c189093bd0edddad50b7a55d6582d0490204d63720e14fc5fb9d901f1aa` |

The two base assets were downloaded from the project's documented v0.1.3
release and verified against its `SHA256SUMS`; current sources were injected
into the test disk/FAT.  This is not a release build and no release URL is
claimed.

## Host checks

Host work is against `feat/bbs-guest-fix` at
`57631e9811febf6457f7196f803757008a28e4e2`.  Patch:
`/output/hermes-templeos.patch`; full modified checkout:
`/output/hermes-templeos/`.

| Check | Result |
| --- | --- |
| `python3 -m pytest -q tests` (before, at 57631e9) | 300 passed, 4 skipped, 1 failed (`test_files_rpc_uses_the_guest_daemon_and_structures_errors`; HRPC probe swallowed the seeded TXFR frame) |
| `python3 -m pytest -q tests` (after) | **305 passed, 4 skipped** |
| `node --import ./tests/js/register-mocks.mjs --test tests/js/*.test.mjs` | **72 passed, 0 failed** |
| `python3 -c "from templeos.tools import tool_specs; ..."` | **exactly 4 tools** (`templeos_vm`, `templeos_screen`, `templeos_input`, `templeos_files`) |
| `python3 evals/measure_schemas.py` before | **1262** |
| `python3 evals/measure_schemas.py` after | **1262** |
| o200k_base delta vs feat/bbs-guest-fix baseline | **0** |

`evals/measure_schemas.py` was not edited.  No tool schema changed and no
fifth tool was added.

## Not done / open issues

- No real community account, refresh credential, or public endpoint was used
  in this sandbox; the host refresh path was exercised with a clearly fake
  fixture client and loopback TLS peer.
- The host patch must be landed by the coordinator on `feat/bbs-guest-fix`;
  it is not committed here.
- No commit, push, merge, tag, publish, or deploy.  All Temple of Hermes
  changes remain uncommitted on `hermes/bbs-token-path`.
