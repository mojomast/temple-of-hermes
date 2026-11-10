# Modem / Net QEMU evidence (COM2 echo)

This directory proves the new `Hermes/Apps/Net` app compiles and runs on
TinkerOS 5.20-rc10 under QEMU TCG, and that the real `Hermes/Net` library
moves bytes both ways over the serial modem path.

## Wiring

| Item | Value |
| --- | --- |
| Guest app | `Hermes/Apps/Net/Run.HC` -> `HermesNetApp` |
| Guest library | `Hermes/Net` (`Glbls`, `Protocol`, `Modem`, `Load`) |
| Networking COM | **COM2** (`0x2F8`, IRQ 3), 115200 8N1 |
| QEMU COM2 socket | `shots/hermes-net-modem/raw/com2.sock` |
| COM1 | left to the Hermes HRPC daemon; the sandbox test only drains it |
| Host peer | `com2_echo_stub.py`, in-memory `LoopbackTransport` |
| Destination | allow-listed name `hermes` only |
| ISO | public TinkerOS 5.20-rc10, sha256 `feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4` |

No BBS, VPS, DNS, deploy, or network device is used (`-nic none`).  The
requested COM1-socket echo was not used because COM1 is the HRPC console;
COM2 is the existing Chat/BBS modem path and keeps HRPC intact.

## Run

```sh
TOH_ISO=/path/to/TinkerOS_5.20-rc10.ISO \
  python3 shots/hermes-net-modem/run_net_test.py
```

The script builds a temporary FAT32 overlay, boots the live CD with two
serial sockets, runs `Run.HC` twice, then calls `HermesNetEchoTest`.  Every
wait is bounded; the VM is stopped with QMP `quit`.

## Result

`com-echo.log` is the saved test transcript.  It shows:

- guest -> stub: `ATZ`, `ATD hermes`, `AT+SEND 18` + `HERMES-NET-ECHO-01`
- stub -> guest: `OK`, `CONNECT hermes`, `OK 18`, and
  `DATA 18` + `HERMES-NET-ECHO-01`
- guest result: `NET_ECHO.RES = 0`, `NET_ECHO_GUEST` has matching
  `tx_len=18 rx_len=18` payloads

`com-echo.at.log` is the host modem's command/byte-count log (payloads are
not logged there).  `run-status.json` records the guest file results and
COM1 run markers.

## Shots

All PNGs are 640x480, use palette indices 0-15 only, and have **0**
off-palette pixels.  Numbers are in `pil-checks.txt` / `pil-checks.json`.

| File | Content |
| --- | --- |
| `02-overlay-listed.png` | overlay mounted as `C:` and listed |
| `03-net-run-first.png` | first `Run.HC` launch, status printed |
| `04-net-run-second.png` | second `Run.HC` launch, usable shell |
| `05-net-echo.png` | `guest->stub` and `stub->guest` bytes, `ECHO OK` |
| `06-shell-usable.png` | `Dir("C:/Tmp")` after the tools, shell prompt |

The PNGs are only processed with Python/PIL (size, palette, bbox,
off-palette count); no image was opened for visual inspection.
