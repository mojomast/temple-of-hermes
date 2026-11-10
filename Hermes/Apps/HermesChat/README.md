# Hermes Chat

Hermes Chat is a small HolyC chat client for the Temple of Hermes COM2
modem.  It compiles the real `Hermes/Net` sources (through
`../../Net/Load.HC`) and dials the allow-listed destination `hermes`; it does
not carry an inline copy of the modem library.

```holyc
Cd("B:/Hermes/Apps/HermesChat");
#include "Run.HC";
```

`Run.HC` opens a terminal window and calls `HermesNetDial("hermes")`.  Type a
message and press Enter; the host relay answers with a `HCHAT1` frame.  `/quit`
hangs up, `/connect` retries, and Shift-Esc closes the window.

Files:

| File | Purpose |
| --- | --- |
| `Load.HC` | Chat UI, icon loading, frame encode/decode; includes `Hermes/Net/Load.HC` |
| `Run.HC` | Entry point: include `Load` and call `HermesChatRun` |
| `README.md` | This note |

The icon is `Hermes/Art/Icons/32/hermes-chat.GR` when present.  The app prints
whether it loaded the real art so a missing overlay is visible.

Protocol and host wiring: `docs/HERMES-CHAT-PROTOCOL.md`.
