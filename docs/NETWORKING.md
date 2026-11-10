# Networking on COM2

The Temple of Hermes keeps **COM1** for the HRPC daemon and puts an optional
**Hayes-style modem** on **COM2**.  Networking is **off by default** and is
**allow-list only**: the guest cannot dial anything the host did not name.

```
guest Hermes/Net  --AT-->  COM2  --QEMU serial-->  host/hermes_modem.py
                                                        |
                                                        +-- allow-listed transport
                                                            (for example "hermes")
```

The host side is a small Python module, `host/hermes_modem.py`.  It is a
library first and a CLI second.  Tests use an in-memory fake transport and
never open a socket, serial port, or other real network resource.

## Safety model

- `HermesModem(enabled=False, ...)` is the default.  While disabled, `ATD`,
  `AT+SEND` and `AT+RECV` answer `ERROR` and the transport is never touched.
- `allow_list` is explicit and empty by default.  An empty list denies every
  destination.  Matching is case-insensitive and exact.
- A denial is logged as `DENY allow-list dest=...` (or
  `DENY disabled dest=...`).
- Payload bytes are never logged; only command text and byte counts are.
- The guest library does not auto-dial at load time.  Nothing happens until
  code calls `HermesNetDial`.

A later chat can dial the allow-listed destination `hermes`:

```python
modem = HermesModem(
    enabled=True,
    allow_list=("hermes",),
    transport=my_transport,
    log_path="run/modem.log",
)
```

## Host AT commands

| Command | Meaning |
| --- | --- |
| `AT` | Attention; replies `OK`. |
| `ATZ` / `AT&F` | Reset, hang up, clear buffers; replies `OK`. |
| `ATI` | Identification text. |
| `ATE0` / `ATE1` | Echo setting; replies `OK`. |
| `ATD <dest>`, `ATDT <dest>`, `ATDP <dest>`, `ATD<dest>` | Dial an allow-listed destination.  Replies `CONNECT <dest>`, `ERROR` (disabled or denied), or `NO CARRIER` (transport failure). |
| `ATH` | Hang up; replies `OK`.  Safe when already idle. |
| `AT+STATUS` | One status line: enabled, connected, destination, allow-list size. |
| `AT+SEND <len>` | Followed by exactly `<len>` raw bytes; replies `OK <n>` or `ERROR`. |
| `AT+RECV <max>` | Replies `DATA <n>` then exactly `<n>` raw bytes, or `ERROR`. |

`AT+SEND` and `AT+RECV` are Hermes extensions.  They keep binary payloads out
of a Hayes `+++` escape and are what the guest `Send` / `Recv` functions use.

Lines may end in CR, LF, or CRLF.  Responses use CRLF.

## Guest library: `Hermes/Net`

Load it from the HolyC command line or another include:

```holyC
#include "/Hermes/Net/Load"
HermesNetDial("hermes");
HermesNetSend("hello",5);
n=HermesNetRecv(buf,sizeof(buf));
HermesNetHangUp;
```

Files:

| File | Purpose |
| --- | --- |
| `Hermes/Net/Glbls.HC` | COM2 constants and connection state. |
| `Hermes/Net/Protocol.HC` | Byte, line, and block helpers over COM2. |
| `Hermes/Net/Modem.HC` | `HermesNetInit`, `Dial`, `Send`, `Recv`, `HangUp`, `Status`. |
| `Hermes/Net/Load.HC` | Include entry point. |

`HermesNetInit` calls `CommInit` only when the COM port table is still empty,
then calls `CommInit8n1(2,115200)`.  Loading `Hermes/Net` after the COM1
daemon therefore does not disturb COM1.  COM2 is `0x2F8`, IRQ 3.

API:

```holyC
Bool HermesNetInit();
Bool HermesNetDial(U8 *dest);          // TRUE only after CONNECT
I64  HermesNetSend(U8 *buf,I64 len);   // len, or -1
I64  HermesNetRecv(U8 *buf,I64 max,I64 timeout_ms=1000); // bytes, 0, or -1
Bool HermesNetHangUp();
U0   HermesNetStatus();
```

`Dial` sends `ATZ`, waits for `OK`, sends `ATD <dest>`, and waits up to five
seconds for `CONNECT`, `ERROR`, `NO CARRIER`, or `BUSY`.  `Send` writes the
`AT+SEND` header and the raw bytes.  `Recv` reads the `DATA <n>` header and
then exactly `<n>` bytes.

## Running the host modem

Library use is the normal path.  For manual experiments:

```sh
# Off by default: dialing answers ERROR.
python3 host/hermes_modem.py

# Allow exactly one destination and bridge AT bytes on stdin/stdout.
python3 host/hermes_modem.py --enable --allow hermes --stdio

# Same, with a command log.
python3 host/hermes_modem.py --enable --allow hermes --stdio --log run/modem.log

# Loopback demo, no network at all.
python3 host/hermes_modem.py --enable --allow hermes --demo
```

The CLI uses a loopback transport so it is safe on an isolated machine.  A
real deployment passes a transport object to `HermesModem`; the transport is
the only component that talks to the outside world.

## QEMU wiring

QEMU stays on TCG with no NIC.  Add a second serial socket next to the COM1
socket:

```sh
qemu-system-x86_64 \
  -machine pc,kernel-irqchip=off -accel tcg -cpu qemu64 \
  -m 2G -smp 1 -vga std -display none -nic none \
  -qmp unix:run/net/qmp.sock,server=on,wait=off \
  -serial unix:run/net/com1.sock,server=on,wait=off \
  -serial unix:run/net/com2.sock,server=on,wait=off \
  -cdrom dist/TempleOfHermes.ISO \
  -boot order=d,menu=on
```

`run/net/com2.sock` is the byte stream that `hermes_modem.py` consumes.  The
modem's network-side transport is separate and remains the deployment's
responsibility.  The sample screenshots in `shots/hermes-net/` come from a
TCG boot with both serial ports present.

## Tests

```sh
python3 -m pytest -q host/tests/test_hermes_modem.py
```

The suite covers off-by-default behavior, allow-list denial, case-insensitive
matching, fake dial, `AT`/`ATZ`/`ATH`, fragmented and batched commands,
binary `AT+SEND` / `AT+RECV`, transport failure, status output, and logging
that omits payload bytes.

## Scope and non-goals

- No raw IP stack, DNS, or TCP in the guest.  COM2 is a modem control channel.
- No automatic dialing, no default destinations, and no network access while
  the modem is disabled.
- COM1 HRPC is unchanged; `Adam/Hermes/` is not modified by this slice.
