# Hermes BBS — QEMU TCG evidence

Guest: TinkerOS 5.20-rc10, installed to a qcow2 disk.
Host: Linux, QEMU `-accel tcg -display none -nic none -machine pc,kernel-irqchip=off`.
ISO SHA-256: `feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4`.

The guest tree contains the real `Hermes/Net` sources (`Glbls.HC`,
`Protocol.HC`, `Modem.HC`, `Load.HC`) plus `Hermes/Apps/HermesBBS`. The app
was compiled in-guest from `C:/Hermes/Apps/HermesBBS/Load.HC`; no inline
network substitute was used.

## Shots

| File | What it shows |
| --- | --- |
| `01-compile.png` / `.txt` | `#include "Load";` compiles `Hermes/Net` + `BBS.HC`; prompt returns |
| `02-cli-help.png` / `.txt` | `HermesBBSCommand("help");` |
| `03-cli-dial.png` / `.txt` | `HermesBBSCommand("dial");` calls `HermesNetDial("bbs")` |
| `04-results.png` / `.txt` | `Dir("C:/Hermes/Apps/HermesBBS/Results");` |
| `05-registry.png` / `.txt` | `Registry.HC` compiled and `HermesAppsRegistryInit();` ran |
| `06-ui.png` / `.txt` | DolDoc board/thread window (offline fallback boards) |

## Result files

`results/001-HELP.json` is a successful local HELP result. It records:

```
"dest":"bbs"
"transport":"hermes-net/com2"
"ok":1
```

`results/001-DIAL.json` and `results/last.json` record a real dial attempt
through `Hermes/Net`:

```
"dest":"bbs"
"transport":"hermes-net/com2"
"op":"DIAL"
"ok":0
"error":"dial_failed"
```

The sandbox had no host modem peer on COM2, so the dial did not reach a BBS.
No external BBS, VPS, or public telnet was contacted; QEMU had no NIC. The
destination is only the allow-list name `bbs`; no hostname, IP, or TLS
endpoint is present in the guest code.

## Commands used

```holyc
Cd("C:/Hermes/Apps/HermesBBS");
#include "Load";
HermesBBSCommand("help");
HermesBBSCommand("dial");
Dir("C:/Hermes/Apps/HermesBBS/Results");
Cd("C:/Hermes/Apps");
#include "Registry";
HermesAppsRegistryInit();
Cd("C:/Hermes/Apps/HermesBBS");
HbbsUiTask(NULL);
```
