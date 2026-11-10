# Hermes Chat and COM2 protocol

Hermes Chat is the first app that uses the B3 COM2 modem from real
`Hermes/Net` sources.  This bee closes the B3 caveat: B3 exercised COM2 with
equivalent inline HolyC, but the `Hermes/Net` library itself was not compiled
by an in-guest HolyC build.  The guest run recorded here compiles
`Hermes/Net/Load.HC` (Glbls, Protocol, Modem) first, then compiles
`Hermes/Apps/HermesChat/Load.HC` and launches it.  Hermes Chat dials the
allow-listed destination `hermes` through that compiled library.

Evidence is under `shots/hermes-app-hermeschat/`.  `build-com1.txt` records
the two COM1 markers emitted only after a successful compile:

```
HERMES_NET_BUILD_OK
HERMES_CHAT_BUILD_OK
```

## Link overview

```
Hermes/Apps/HermesChat  --HCHAT1 frame-->  Hermes/Net (compiled)  --AT--> COM2
                                                                          |
                                                               host/hermes_chat_relay.py
                                                                          |
                                                                     "hermes"
```

COM1 remains the Hermes HRPC console.  Hermes Chat never touches COM1 except
that the optional build-check helper writes a marker there when the shell has
not initialised it yet.

## Guest library: Hermes/Net

Entry point:

```holyc
#include "B:/Hermes/Net/Load.HC";
```

or, from a directory next to `Net`:

```holyc
Cd(__DIR__);;
#include "../../Net/Load.HC"
```

Files:

| File | Purpose |
| --- | --- |
| `Glbls.HC` | COM2 constants, connection state, destination |
| `Protocol.HC` | byte, line, and block helpers over COM2 |
| `Modem.HC` | `HermesNetInit`, `Dial`, `Send`, `Recv`, `HangUp`, `Status` |
| `Load.HC` | include entry point: Glbls, Protocol, Modem |
| `Build.HC` | in-guest compile check and COM1 marker |

API:

```holyc
Bool HermesNetInit();
Bool HermesNetDial(U8 *dest);          // TRUE only after CONNECT
I64  HermesNetSend(U8 *buf,I64 len);   // len, or -1
I64  HermesNetRecv(U8 *buf,I64 max,I64 timeout_ms=1000); // bytes, 0, or -1
Bool HermesNetHangUp();
U0   HermesNetStatus();
```

The compiled sources include include guards because Hermes Chat includes Net
after the build check may already have compiled it in the same HolyC session.
The guards do not change the wire behavior.

## AT layer on COM2

COM2 is 115200 8n1.  The guest speaks a small Hayes subset:

| Command | Reply | Meaning |
| --- | --- | --- |
| `AT` | `OK` | attention |
| `ATZ` / `AT&F` | `OK` | reset and hang up |
| `ATI` | `Temple of Hermes chat relay` | identification |
| `ATE0` / `ATE1` | `OK` | echo setting |
| `ATD <dest>` / `ATDT <dest>` / `ATDP <dest>` | `CONNECT <dest>` | dial an allow-listed destination |
| `ATH` | `OK` | hang up |
| `AT+STATUS` | `STATUS ...` | state without message payload |
| `AT+SEND <len>` | `OK <len>` after the raw bytes | send one chat frame |
| `AT+RECV <max>` | `DATA <n>` followed by exactly `n` bytes | fetch queued data |

`ATD` returns `ERROR` while the relay is disabled or when the destination is
not in the allow-list, and `NO CARRIER` if a transport fails.  Lines may end
in CR, LF, or CRLF; responses use CRLF.

## Chat frame

Each `AT+SEND` payload is exactly one UTF-8/ASCII frame:

```
guest -> host:   HCHAT1 <text>
host -> guest:   HCHAT1 <text>
host -> guest:   HCHAT1-ERR <reason>
```

`<text>` is one line; the relay replaces embedded CR/LF with spaces before
queueing a reply.  An empty body is allowed and is answered with a help line.
A payload without the `HCHAT1 ` prefix gets an `HCHAT1-ERR bad frame` reply;
the AT layer itself still returns `OK <len>` because the bytes were accepted.

Examples:

```
> ATZ
< OK
> ATD hermes
< CONNECT hermes
> AT+SEND 19
> HCHAT1 hello hermes
< OK 19
> AT+RECV 768
< DATA 33
< HCHAT1 Hermes heard: hello hermes
> AT+SEND 11
> HCHAT1 ping
< OK 11
> AT+RECV 768
< DATA 11
< HCHAT1 pong
> ATH
< OK
```

## Host relay: host/hermes_chat_relay.py

The relay is a library first and a CLI second.  It is **off by default** and
**allow-list only**.  An empty allow-list denies every destination.

```python
from hermes_chat_relay import HermesChatRelay

relay = HermesChatRelay(
    enabled=True,
    allow_list=("hermes",),
    log_path="run/modem.log",
)
reply = relay.feed(b"ATD hermes\r")
```

Default responder (`HermesResponder`) is deterministic and offline, so the
sandbox run needs no network:

| Guest text | Reply |
| --- | --- |
| empty | `Say something and I will answer.` |
| `ping` / `/ping` | `pong` |
| `help` / `/help` | short command help |
| `hi`, `hello`, `hey` | `Hello from Hermes.` |
| anything else | `Hermes heard: <text>` |

A deployment can pass any object with `reply(text) -> str`, or use
`ScriptedResponder` / `CallableResponder` in tests.

Logging records commands and byte counts.  Message payloads are **not**
logged unless `log_messages=True` is passed explicitly.

Run it against a QEMU COM2 unix socket:

```sh
python3 host/hermes_chat_relay.py \
  --enable --allow hermes \
  --connect run/hermes-chat/com2.sock \
  --log shots/hermes-app-hermeschat/modem.log
```

Other modes: `--stdio` bridges AT bytes on stdin/stdout; `--demo` runs an
in-memory transcript.

## Guest app: Hermes/Apps/HermesChat

Files:

| File | Purpose |
| --- | --- |
| `Load.HC` | chat UI, icon loading, frame encode/decode; includes `../../Net/Load.HC` |
| `Run.HC` | entry point: include `Load`, call `HermesChatRun` |
| `README.md` | short user note |

`Load.HC` finds the checked-in `Hermes/Art/Icons/32/hermes-chat.GR` under
`::`, `B:`, `C:`, `T:`, or `~/Hermes` and loads it with `GRRead`.  The chat
window prints `art: hermes-chat 32x32 loaded` when the real icon was found;
otherwise it prints `art: text fallback`.

At startup the app calls `HermesNetDial("hermes")`, prints
`connected: CONNECT hermes`, and prompts with `you>`.  Each entered line is
sent as one `HCHAT1` frame, and the reply is printed as `hermes> ...`.
`/connect` retries the dial, `/quit` hangs up, and Shift-Esc closes the window.

## In-guest build and run

The sandbox used the public TinkerOS 5.20-rc10 ISO:

```
sha256 feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4
```

QEMU was TCG only:

```
-accel tcg -cpu qemu64 -m 2G -smp 1 -vga std -display none -nic none
-machine pc,kernel-irqchip=off
-qmp unix:<run>/qmp.sock,server=on,wait=off
-serial unix:<run>/com1.sock,server=on,wait=off
-serial unix:<run>/com2.sock,server=on,wait=off
-cdrom TinkerOS_5.20-rc10.ISO
-boot order=d,menu=on
-drive file=<run>/overlay.img,format=raw,if=ide,index=1,media=disk
```

The ISO was booted live (answer `n` to install, then `n` to the tour).  A
64 MiB MBR+FAT32 overlay disk supplied the sources as 8.3 names and a short
`RUN.HC` copied them to the RAM drive `B:/Hermes`.  This avoids any
host-specific ISO or source path in the guest.

Commands typed at the HolyC shell:

`Mount;` was driven with `C`, Enter (all partitions), `p` (probe), `2` (the
ATA hard disk), then Enter to leave the mount menu.  Then:

```holyc
#include "C:/RUN.HC";       // copy sources to B:/Hermes
#include "B:/Hermes/Net/Build.HC";
HermesNetBuildCheck;        // prints HERMES/NET BUILD OK + COM1 marker
#include "B:/Hermes/Apps/HermesChat/Load.HC";
HermesChatBuildCheck;       // prints HERMES/CHAT BUILD OK + COM1 marker
#include "Run.HC";           // launch (cwd is the app directory)
```

The Net build output on screen was:

```
HERMES/NET BUILD OK
COM2  baud=115200  line_max=256  dest_max=64
HERMES/NET COM2 idle (host modem off by default)
```

The chat build output was:

```
HERMES/CHAT BUILD OK
destination=hermes  net=idle
art=hermes-chat 32x32 loaded
```

There were no compiler errors or warnings in the final run.

## Runtime evidence

`shots/hermes-app-hermeschat/`:

| File | Content |
| --- | --- |
| `04-net-build.png` / `.txt` | `HERMES/NET BUILD OK` after compiling the real Net sources |
| `05-chat-build.png` / `.txt` | `HERMES/CHAT BUILD OK`, icon loaded |
| `06-chat-connected.png` / `.txt` | Hermes Chat window, `connected: CONNECT hermes` |
| `07-chat-hello.png` / `.txt` | `you> hello hermes` -> `hermes> Hermes heard: hello hermes` |
| `08-chat-ping.png` / `.txt` | `you> ping` -> `hermes> pong` |
| `09-chat-quit.png` / `.txt` | `/quit` returns to the shell |
| `build-com1.txt` | both COM1 compile markers |
| `modem.log` | `DIAL dest=hermes result=connect`, send/recv counts, `HANGUP` |
| `run-status.json` | QEMU pid, screenshot list, markers |

The modem log shows no message payload, only command text and byte counts.

## Tests

```sh
python3 -m pytest -q host/tests/test_hermes_chat_relay.py
```

The suite covers off-by-default behavior, empty and explicit allow-lists,
case-insensitive matching, dial forms, `AT`/`ATZ`/`ATH`, fragmented input,
`AT+SEND`/`AT+RECV` framing, malformed frames, responder failures, payload
discard after a denied send, status output, and logging that omits chat text.

## Safety and non-goals

- Networking is off by default; only an explicit `enabled=True` plus an
  allow-list containing `hermes` permits a dial.
- No raw IP stack, DNS, or TCP in the guest.
- No auto-dial at load time; Hermes Chat dials only after the user launches it.
- COM1 HRPC is unchanged.
- The relay's network side is an in-process responder by default; a real
  deployment can substitute its own responder/transport.
