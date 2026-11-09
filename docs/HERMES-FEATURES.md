# THE TEMPLE OF HERMES — features, research, and protocol

Branch `hermes/v0`, image version 0.1.0, based on TinkerOS 5.20-rc10
(`b8d1703b73fd027a35ede9b6e37ae9430e49f1bb`).

Upstream: https://github.com/tinkeros/TinkerOS (Unlicense / public domain).
TempleOS itself is public domain by Terry A. Davis.

## What an agent and a user sharing one VM actually need

The hermes-templeos plugin already proved, in a QEMU bake-off, that TinkerOS
is the right base: absolute QMP clicks work (VMMouse) and Adam `Comm*` serial
works. Stock TempleOS 5.03 and ZealOS failed one or both of those. The plugin
still has to:

- Guess on-screen text with 8×8 glyph OCR (about 96–99 % on a clean TinkerOS
  frame, worse when the clock, sprites, or a dialog overlap the cells).
- Infer "the VM is idle" from cropped frame hashes (the title-bar clock never
  stabilizes a full-frame hash).
- Share one mouse cursor and one keyboard with the user, with only a host-side
  arbiter (watch / shared / user) and no in-guest cue of who is driving.
- Walk into the first-boot "Install onto hard drive?" and "Take Tour" `YorN`
  prompts, or into `Fmt` / `OSInstall`, by sending a single `y`.

A guest that is *designed* for co-use should give the agent a structured
channel, ground-truth text, events, a visible driver mode, a ready-to-work
boot, and hard stops in front of destructive operations. Those are the six
features shipped in v0.1.0.

## Research: what already existed

| Project | What it already did | What it did not do |
| --- | --- | --- |
| TempleOS 5.03 | `Comm.HC` demo driver, DolDoc clipboard (`sys_clip_doc`), `DocDump` / `DocScanLine`, `TaskRep`, first-boot `Once.HC` install/tour `YorN`, `Fmt(..., confirm=TRUE)` | No agent daemon, no window-text export over serial, no driver banner, no event stream, no boot-to-ready, no agent-aware format guard |
| TinkerOS 5.20-rc10 | In-tree `Adam/Device/Comm.HC` (CommInit disabled at boot on purpose), TOSClient (a *client* that talks to a host "snail" helper: files, URL fetch, clipboard, host exec), VMMouse, nicer VM installer | TOSClient is not a guest RPC server. Same Once.HC install/tour prompts. No presence, no DolDoc export, no events, no agent guards |
| ZealOS | Modernized fork, AHCI, 1024×768. Used in the plugin bake-off | Absolute clicks failed in that bake-off; no Hermes-style co-use agent |
| Spirit (und3f/temple-os-apps) | Closest prior art. A boot-time guest agent over serial: exec HolyC in a new window or silently, get/set the clipboard. Host client talks TCP-serial | No window/task listing, no exact text dump, no event stream, no AGENT/USER banner or second cursor, no skip-install boot, no format/install guards |
| TOSClient clipboard cmds | `CMD_GET_CB_TEXT` / `CMD_SET_CB_TEXT` against a *host* daemon | Opposite direction of a guest server; not an agent protocol |
| temple-cua | Host-side computer-use bench: the model sees screenshots and types into QEMU. UART task is a *benchmark*, not a productized guest agent | No in-guest daemon or co-use UX |
| hermes-templeos Xfer.HC | Framed `TXFR` list/pull/push on COM1, loaded by the agent after `CommInit` | Files only; not running at boot; no text/events/mode |

Conclusion: a structured *guest* RPC with exact DolDoc export, a visible
AGENT/USER presence, an event stream, a skip-install Hermes boot, and
agent-blocked `Fmt`/`OSInstall` have not been done in TempleOS, TinkerOS, or
ZealOS. Clipboard sync has, so v0.1.0 includes it as a daemon op but does not
claim it as new.

## Chosen features (and why)

Picked by value to the hermes-templeos agent/user loop versus what we could
ship in HolyC and prove under QEMU TCG.

1. **Hermes agent daemon (HRPC)** — highest leverage. One COM1 channel the
   plugin can keep as the serial backend of the existing four tools.
2. **Exact screen-text export** — directly replaces the weakest plugin path
   (`read_text` glyph OCR) with ground truth plus cursor coordinates.
3. **Presence banner and distinct agent cursor** — the user has to *see* who
   is driving; the host arbiter alone is invisible inside the pane.
4. **Event stream** — lets `wait_idle` become "no prompt, no new windows, no
   compile error" instead of a cropped hash hope.
5. **Boot to Hermes-ready** — first-boot `YorN` was already burning real
   sessions. Branding and the `HBEACON` are how the host knows the flavor.
6. **Safe-mode guards** — a single injected `y` must not format a disk. Hooked
   at `YorN` / `AreYouSure` / `Fmt` in the kernel and at `OSInstall` /
   `BootHDIns` in Adam.

### Deferred (future work)

- Claiming a "world first" shared clipboard (Spirit / TOSClient already did
  host-guest clip). The RPCs are there (`clip_get`, `clip_set`).
- A second serial port so HRPC and a raw console never share COM1. v0.1.0
  multiplexes on COM1 only; networking stays off (`-nic none`).
- Hooking `GetChar` itself (not just `YorN`) so every blocked read becomes a
  `prompt_waiting` event. Today we also poll the focused DolDoc for
  `(y or n)`, `ARE YOU SURE`, and `Press a key`.
- Rebase onto TinkerOS 5.24 (current `main`). This branch stays on 5.20-rc10
  because that is the ISO the plugin bake-off pinned.
- USB / bare-metal images, higher default resolution, and a documented
  supplementary-ISO path for people who want to keep a stock TinkerOS kernel
  and only drop `/Adam/Hermes`.

## Guest layout

| Path | Role |
| --- | --- |
| `Adam/Hermes/Load.HC` | Included from `MakeHome.HC`; compiles the daemon and calls `HermesInit` |
| `Adam/Hermes/Daemon.HC` | Hidden task `HermesDaemon`, COM1 RPC loop |
| `Adam/Hermes/Text.HC` | `HermesDocPlain` / focus / all-window JSON |
| `Adam/Hermes/Events.HC` | Ring + poller + `HEVT` flush |
| `Adam/Hermes/Presence.HC` | Wraps `gr.fp_wall_paper` and `gr.fp_draw_ms` |
| `Adam/Hermes/Guards.HC` | Sets kernel `fp_input_gate` |
| `Adam/Hermes/MakeDistro.HC` | Build-time only; **not** included from `Load.HC` |
| `Once.HC` | Skips install and tour; prints the welcome |
| `Doc/Start.DD` | Title: THE TEMPLE OF HERMES |
| `Kernel/StrC.HC`, `Kernel/BlkDev/DskFmt.HC`, `Kernel/KGlbls.HC`, `Kernel/KernelC.HH` | `fp_input_gate` hook |
| `Misc/OSInstall.HC`, `Adam/Opt/Boot/BootHDIns.HC` | Same hook at the entry of install / BootHDIns |

`CommInit` + `CommInit8n1(1,115200)` run inside `HermesInit`. Upstream leaves
`CommInit` commented out in `Adam/Device/Comm.HC` to speed boot; this fork
turns COM1 on because the daemon is the point of the image.

## Protocol spec

Line-oriented, then a raw payload of exactly `len` bytes. Little-endian is
only used for the `push` / `pull` file bodies (raw bytes). No JSON parser is
required of the guest; the guest *emits* a JSON-ish subset (ASCII, escaped
`"`, `\`, newlines) and *accepts* raw or simple text payloads.

Charset: ASCII. Do not send DolDoc `$$` on the wire; the daemon escapes
non-printable bytes out of JSON strings.

### Beacon

Sent once when the daemon task starts, and only then:

```
HBEACON TempleOfHermes/0.1.0\n
```

The host should keep COM1 open for the whole session; bytes sent before the
guest is ready are lost, same as any TempleOS serial port.

### Request

```
HREQ <id> <op> <len>\n
<payload of len bytes>
```

- `<id>` is a decimal integer chosen by the host (they should be unique enough
  to match replies; they need not be monotonic).
- `<op>` is one of the names below, `[A-Za-z_]`.
- `<len>` is decimal, 0..262144. The payload is *not* newline-terminated
  unless the caller included a newline in it.

### Reply

```
HRPL <id> <ok|err> <len>\n
<payload of len bytes>
```

`<id>` echoes the request. `err` payloads are short ASCII reasons:
`unknown_op`, `len`, `bad_mode`, `no_task`, `pull_size`, `pull_read`,
`push_path`, `push_write`.

### Events

Emitted whenever the daemon loop polls, including while a request is not in
flight (they can appear between a request and its reply — the host must be
ready to parse `HEVT` first):

```
HEVT <seq> <kind> <len>\n
{"seq":N,"t":123.456,"kind":"...","data":"..."}
```

Kinds: `ready`, `task_spawned`, `window_opened`, `prompt_waiting`,
`compile_error`, `mode_changed`, `danger_blocked`.

`data` is a short escaped string (task title, prompt snip, blocked function
name, version, …). `prompt_waiting` is edge-triggered: a new event only when
the snip changes or a prompt appears after a quiet period.

### Operations

| Op | Payload | Reply payload |
| --- | --- | --- |
| `ping` | ignored | `{"pong":1,"t":...,"mode":"...","version":"0.1.0"}` |
| `help` | ignored | JSON list of ops, name, version |
| `eval` | raw HolyC source | `{"ok":0|1,"text":"..."}`. Stdout/except text captured. Failures also emit `compile_error` |
| `tasks` | ignored | `{"focus":"0x...","tasks":[{addr,name,title,win,show,focus},…]}` |
| `focus` | empty to query; `0xADDR` or a window title to switch | same shape as `tasks` |
| `mouse` | empty to query; `x,y` to record the agent pointer (and `MsSet` in AGENT mode) | `{"x","y","z","lb","rb","agent_x","agent_y","mode"}` |
| `text` | `focus` (default) or anything containing `all` | one window object, or `{"windows":[…]}`. Each object has `text`, `cursor` `{x,y,line,col}`, `win` `[l,t,r,b]`, `title`, `focus` |
| `mode` | `user`, `shared`, or `agent` | `{"mode":"..."}`. Emits `mode_changed` |
| `clip_get` | ignored | `{"text":"..."}` from `sys_clip_doc` |
| `clip_set` | raw text | `clip_get` after the set |
| `list` | path (default `/`) | JSON array of `{name,is_dir}` |
| `pull` | path | **raw file bytes** (not JSON), length in the header |
| `push` | `path` + NUL + raw bytes | `{"wrote":N}` |
| `events` | ignored | JSON array of pending events (also drains the ring) |
| `idle` | ignored | `{"t","mode","prompt","evt_pending","ready"}` |

### Modes

- `user` (default at boot): the human drives. Kernel/install guards are off.
  The second cursor is hidden.
- `shared`: both may type. Ordinary `YorN` is allowed so the human can answer
  a dialog. `Fmt`, `AreYouSure`, `OSInstall`, `BootHDIns` still refuse. The
  agent crosshair is drawn at the last agent `mouse` coordinates.
- `agent`: the daemon treats this session as agent-driven. All of the above
  plus `YorN` refuse, returning NO. The hardware cursor tracks the agent; the
  distinctive yellow crosshair is also drawn on top of the stock black arrow.

### Guards

`fp_input_gate` is a kernel function pointer, default `NULL` (stock behavior).
`HermesInit` points it at `HermesInputGate`. The hook returns FALSE to refuse.

When it refuses it prints a one-line notice in the current doc and pushes
`danger_blocked`. This is compiled into the ISO's `Kernel.BIN.C` by
`BootDVDIns`; a stock TinkerOS kernel will not have the symbol, which is why
the official image must be rebuilt with `scripts/build_iso.py` rather than
file-copied onto a live CD.

## Building and proving

See the top-level README. `scripts/build_iso.py` boots the pinned TinkerOS
ISO, drives the official VM installer (one 640×480 partition, no extras, no
reboot), serial-pushes the overlay onto `C:`, then `#include`s
`/Adam/Hermes/MakeDistro.HC`, which is TinkerOS `DoDistro`/`BootDVDIns`/
`RedSeaISO` writing `/Tmp/TempleOfHermes.ISO.C`. The host extracts that file
from the FAT32 partition of the qcow2.

`scripts/smoke.py` boots the new ISO, waits for `HBEACON`, and exercises
ping, text, mode, mouse, eval, events, guards, clipboard, and list, writing
PNGs and a serial transcript into `shots/`.
