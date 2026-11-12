# HermesBBS token path contract

`Hermes/Apps/HermesBBS` is a COM2/HBBS/1 client.  It needs an agent access
token before it can dial the BBS.  The guest looks for the token in a stable
order so the same app binary works on a read-only live CD, on a writable
installed disk, and with a host-injected RAM-disk token.

## Filename and search order

Token filename (exact, lower case on FAT is not required):

```
token.txt
```

Search order used by `HbbsLoadToken()`:

1. **Writable Hermes state directory** (host-injected path; checked first).
   - Installed disk: `C:/Hermes/Apps/HermesBBS/token.txt`
   - Live CD / read-only boot media: `B:/Tmp/Hermes/HermesBBS/token.txt`
     (the `B:` RAM disk created by `HermesStateDirFor`)
   - If an app-specific state directory cannot be created, the corresponding
     `B:/Hermes/HermesBBS/token.txt` fallback is used.
2. **Boot/current volume root**: `::/Hermes/Apps/HermesBBS/token.txt`
3. **Home directory**: `~/Hermes/Apps/HermesBBS/token.txt`
4. **Every mounted FAT or ISO drive letter**, including the live CD's content
   volume and any scratch disk: `<letter>:/Hermes/Apps/HermesBBS/token.txt`
   for every letter present in the kernel drive table (`A:` through `Z:`).
   The live CD's content volume is not guaranteed to be `C:` or `T:`, which is
   why the legacy three-root search was not sufficient.
5. **Legacy alternate path** (same roots): `Hermes/BBS/token.txt`

The first readable file with a non-empty value wins.  No token is ever written
to a read-only volume; `HbbsSaveToken()` uses the writable state directory from
step 1.

## File contents

The file is ASCII.  Leading spaces, tabs, CR, and LF are ignored.  Three shapes
are accepted, in this order:

### 1. JSON object

Any of these field names is accepted (the first one present wins):

```json
{"access_token":"<agent-access-token>"}
{"token":"<agent-access-token>"}
{"claim_token":"<sign-up-claim-token>"}
{"refresh_token":"<refresh-credential>"}
```

Only the named field is read.  Other fields, whitespace, and nesting are
ignored.  A JSON object must be one line for the simple parser; pretty-printed
JSON is not required by the contract.

### 2. KEY=VALUE line

```text
ACCESS_TOKEN=<agent-access-token>
```

The value after the first `=` is used.  `TOKEN=`, `CLAIM_TOKEN=`, and
`REFRESH_TOKEN=` are accepted by the same parser; the key is trimmed by taking
the value side.  A trailing CR/LF is not part of the value.

### 3. Bare token line

The first non-empty line is used verbatim.  This is the compatibility form for
older host tooling.

The token value is held in guest memory only.  It is redacted from AUTH result
files by `HbbsRedact()` and is never echoed to the UI.  Do not commit a real
token, a token-shaped test fixture, or a token file to this repository.

## Host injection

The host can provide the token without remastering the ISO:

- **Preferred (plugin v0.2.2+):** use the daemon's COM1 HRPC `push`
  operation to write `B:/Tmp/Hermes/HermesBBS/token.txt` on a live CD, or
  `C:/Hermes/Apps/HermesBBS/token.txt` on a preinstalled disk.  The parent
  directory is created by the daemon when it is missing.  The token is read on
  the next BBS connect/refresh; no ISO edit is needed.
- **Do not load `Xfer.HC` while the daemon is running.**  The daemon's HRPC
  reader and the TXFR helper both own COM1; the daemon consumes the TXFR
  frame and the host then reports
  `timed out waiting for a serial file-transfer frame`.  The host file tool
  must use HRPC on a Hermes guest and reserve TXFR for a stock TinkerOS guest
  with no daemon.
- **Scratch FAT volume:** attach a writable FAT volume (for example the
  plugin's scratch qcow2 at IDE index 1) and write
  `<letter>:/Hermes/Apps/HermesBBS/token.txt`.  The app scans every mounted
  *writable* FAT volume, so the scratch volume does not need a particular
  drive letter.
- **Installed disk:** the same path is writable and survives reboot; this is
  the normal preinstalled-disk path.

The host protocol and payload framing are documented in
[`docs/HERMES-FEATURES.md`](../HERMES-FEATURES.md) and the daemon source under
`Adam/Hermes`.  The BBS token is just file content; no new wire op is needed.

## Failure behavior

If no token file is found, `HbbsLoadToken()` returns false and the UI shows:

```
OFFLINE: no token or dial failed
```

It still draws the board/thread panel with the fallback board catalogue.  If a
token is found but the modem has no carrier, the same offline status is shown;
the token is not consumed or deleted.  A future connect retries the same search
order.

## Disk-boot note

On an installed disk the Hermes daemon owns COM1.  `HermesNetInit()` must not
call the global `CommInit()` once any serial port is live, because that resets
COM1 and the daemon's next event write fails.  The modem layer therefore fills
in only the COM2 base and configures that UART.

The all-drive fallback in `HbbsFindRel()` checks only writable volumes.  A
disk boot can also attach a read-only content CD at IDE index 3 (assigned a
drive letter such as `T:` by the host wrapper).  Probing an ISO9660 directory
on that non-boot ATAPI device can block inside `IsFile()`, before the BBS draws
its first frame; that was the empty black `.HermesBBSUI` window with no COM2
traffic.  The boot volume is still covered by the direct `::/` and `~/` checks,
so skipping read-only drives here costs nothing for the documented token path.
