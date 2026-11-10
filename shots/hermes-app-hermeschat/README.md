# Hermes Chat QEMU evidence

Captured from a live TinkerOS 5.20-rc10 boot under QEMU TCG with no NIC and
two serial ports (COM1 HRPC/marker, COM2 modem).  The public ISO SHA-256 is
`feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4`.

The source tree was supplied on a temporary MBR+FAT32 overlay disk as 8.3
names, then copied to the guest RAM drive at `B:/Hermes`.  The compile helpers
in `Hermes/Net/Build.HC` and `Hermes/Apps/HermesChat/Load.HC` emitted markers
on COM1 only after the actual sources compiled.

| File | Content |
| --- | --- |
| `00-boot-prompt.png` | TinkerOS boot prompt before live boot |
| `01-live-desktop.png` | live desktop |
| `02-mounted.png` | overlay mounted as C: through the Mount prompt |
| `03-overlay.png` | `C:/RUN.HC` copied the sources to `B:/Hermes` |
| `04-net-build.png` | actual `Hermes/Net` source compile: `HERMES/NET BUILD OK` |
| `05-chat-build.png` | Hermes Chat compile: `HERMES/CHAT BUILD OK`, icon loaded |
| `06-chat-connected.png` | Hermes Chat dialed `hermes`: `connected: CONNECT hermes` |
| `07-chat-hello.png` | `hello hermes` -> `Hermes heard: hello hermes` |
| `08-chat-ping.png` | `ping` -> `pong` |
| `09-chat-quit.png` | `/quit` returned to the shell |
| `99-final.png` | final screen before QEMU quit |
| `build-com1.txt` | both COM1 compile markers |
| `modem.log` | dial, send/recv byte counts, hangup (no payload text) |
| `run-status.json` | QEMU pid, shot list, markers |

Each PNG has a matching `.txt` produced by the TempleOS glyph OCR.
