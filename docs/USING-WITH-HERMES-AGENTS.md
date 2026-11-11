# Using Temple of Hermes efficiently with Hermes agents

This guide is for a human running THE TEMPLE OF HERMES with the
[`hermes-templeos`](https://github.com/mojomast/hermes-templeos) plugin, and for
the agent driving it. It covers the four plugin tools, the guest serial
channel, low-token habits, and launcher autostart.

Sources: `PLUGIN-INTEGRATION.md` (the four-tool mapping),
[`HERMES-FEATURES.md`](HERMES-FEATURES.md) (the HRPC protocol), and `Once.HC` /
`HomeSys.HC` (installed as `/Home/HomeSys.HC`; the boot and startup path).
This branch does not change the plugin itself.

## The short version

1. Start the VM with `templeos_vm` and wait for the `HBEACON` line. On this
   0.1.2 build the daemon string may still read
   `HBEACON TempleOfHermes/0.1.0`.
2. Set the mode you want: `user`, `shared`, or `agent`.
3. Read the focused window with `templeos_screen` using the **text** path, not
   a screenshot.
4. Act with `templeos_input` (`holyc`, `type`, `keys`, `click`, `move`).
5. Move files with `templeos_files`; do not type long file contents through the
   keyboard.
6. Use screenshots only when you must verify pixels, art, or a visual layout.

## The four tools

The plugin keeps a four-tool contract. Do not add a fifth tool for a new
feature; extend the existing request fields instead.

### `templeos_vm`

- `start` boots the Hermes image and opens COM1. Wait for the beacon before
  sending anything. The guest has already run `CommInit8n1(1,115200)`; do not
  type it again.
- `status` reports the host state and, on the Hermes flavor, the beacon, mode,
  and readiness.
- `stop`, `reset`, `snapshot`, `restore`, `doctor` stay host-side. `snapshot`
  still ejects the floppy first, as in the TinkerOS bake-off.
- `doctor` checks the ISO hash. The expected artifact is
  `TempleOfHermes-0.1.2.ISO`.

### `templeos_screen`

- `read_text` should use the guest `text` RPC. It returns the DolDoc plain text
  of the focused window (or all visible windows when asked), with cursor and
  window geometry. This is ground truth, not glyph OCR.
- `look` and `hash` use QMP screendumps. Use them for visual checks, not for
  ordinary reading.
- `wait_idle` should prefer the `idle` RPC plus `events`. A pending
  `prompt_waiting` or `compile_error` means the machine is not idle. Keep the
  cropped-hash fallback only for the case where serial is down.

### `templeos_input`

- `holyc` should use the `eval` RPC so stdout and compile errors come back as
  text and a `compile_error` event is emitted. Fall back to typing only if the
  daemon is unavailable.
- `type`, `keys`, `click`, and `move` stay on QMP / VMMouse so the human can
  also drive the pane. After an agent `move` or `click`, send the guest
  `mouse x,y` RPC so the agent crosshair follows.
- Mode / presence belongs here (or in `templeos_vm status`). Keep the host
  arbiter and the guest banner in agreement:
  - host `user` ↔ guest `mode user`
  - host `shared` ↔ guest `mode shared`
  - host "agent acting" ↔ guest `mode agent`

### `templeos_files`

- `list`, `pull`, and `push` should use the HRPC ops of the same names.
- `pull` returns raw bytes in the HRPC payload; `push` takes `path + NUL + raw
  bytes`.
- Do not load `Xfer.HC` on COM1 while HRPC is running. Pick one framing.

## Low-token habits that matter

The screen is a 640×480 VGA frame; a screenshot is large and often ambiguous.
The serial channel is tiny and exact. Prefer text.

1. **Read text, not pixels.** `templeos_screen read_text` over the `text` op is
   smaller and exact. Use `focus` by default; ask for `all` only when the
   focused window is not the one you need.
2. **Ask for the idle signal, not a hash.** `idle` and `events` tell you when a
   prompt, compile error, or new window appeared. A cropped hash changes with
   the clock, the banner, and the agent cursor.
3. **Evaluate, do not type.** `eval` returns stdout and errors directly. Typing
   a long HolyC snippet through `keys` costs tokens and is fragile.
4. **Batch text work.** One small `eval` that prints exactly the fields you need
   is cheaper than several round trips.
5. **Keep replies narrow.** Prefer `tasks` for a task list and `text`
   `focus` for one window; do not dump every window on every turn.
6. **Use `files` for content.** Pull a file and read it on the host; push edited
   content back. Do not replay a file through the keyboard.
7. **Screenshot only to verify visuals.** Art, layout, or "did the banner draw"
   are legitimate screenshot cases. Reading a command result is not.
8. **Respect the mode.** In AGENT mode, install/format prompts refuse and emit
   `danger_blocked`. Do not fight the guard; switch to USER with the human if a
   destructive operation is genuinely needed.
9. **Reuse the event ring.** Drain `events` before waiting; stale events are
   cheaper than repeating a screenshot loop.
10. **Close the loop.** After a click or mode change, read `status` or `text`
    once to confirm, then stop.

## The serial channel

The daemon is loaded from `Adam/Hermes/Load.HC` during startup, after the
VMMouse and OPL setup in `Home/MakeHome.HC`. It opens COM1 at 115200 8n1.

### Frames

```text
HBEACON TempleOfHermes/0.1.0
HREQ <id> <op> <len>\n + <len bytes of payload>
HRPL <id> <ok|err> <len>\n + <len bytes>
HEVT <seq> <kind> <len>\n + <len bytes of JSON>
```

The beacon is sent once when the daemon task starts. The version in that
string is the daemon's own value; on this 0.1.2 image it can still read
`0.1.0`. Bytes sent before the beacon are lost, as with any TempleOS serial
port. Keep COM1 open for the session.

### Operations

| Op | Use |
| --- | --- |
| `ping` | Liveness and mode/version. |
| `help` | Op list, name, version. |
| `eval` | Run HolyC; returns captured stdout and errors. |
| `tasks` | Task list, focus, window, visibility. |
| `focus` | Query or switch focus by address or title. |
| `mouse` | Query, or record the agent pointer / move in AGENT mode. |
| `text` | Focused window or all visible windows with cursor geometry. |
| `mode` | `user`, `shared`, or `agent`; emits `mode_changed`. |
| `clip_get` / `clip_set` | Clipboard over serial (prior art credited). |
| `list` | Directory listing. |
| `pull` / `push` | Raw file transfer. |
| `events` | Pending event ring (drains it). |
| `idle` | Ready/prompt/event summary. |

Event kinds: `ready`, `task_spawned`, `window_opened`, `prompt_waiting`,
`compile_error`, `mode_changed`, `danger_blocked`.

The full payload shapes and guard semantics are in
[`HERMES-FEATURES.md`](HERMES-FEATURES.md).

## Launcher autostart

This branch ships the full-screen Hermes launcher and starts it from
`Once.HC` after the welcome text. The launcher reads
`Hermes/Apps/Registry.HC` and presents all 18 entries in a 6x3 grid.

- Click an icon or press its shortcut key.
- Arrow keys move the selection; Enter or Space opens it.
- `F1` opens About. `Temple` keeps you on the home screen.
- `Launcher/RunFile.HC` runs an app in its own visible task and restores the
  launcher when the app exits.
- The launcher searches `::`, `T:`, `C:`, and `~/` for `Hermes/Apps`, so the
  same files work from a live CD, an installed disk, or a serial-pushed
  overlay.

`Once.HC` calls `HermesStartApps`, which only starts the launcher when
`Hermes/Apps/Launcher/Run.HC` exists. Do not spawn it from `Adam` or from the
Hermes daemon, and do not add install, format, or disk-write actions to it.
Let `fp_input_gate` enforce the mode guards.

Keep the launcher's own startup messages short. The boot path already prints
the product name and version; do not repeat them on every window.

## A safe first session

Pseudo-call sketch (the plugin exposes these as tool actions, not a Python API):

```text
templeos_vm(start)                    # wait for HBEACON
templeos_screen(read_text)            # focus text, not a screenshot
templeos_input(holyc, "6*7;")         # eval, read the result
templeos_vm(status)                   # mode + ready
templeos_input(mode, "agent")         # only when the human agrees
templeos_screen(read_text)            # confirm the banner/mode text
templeos_input(mode, "user")          # hand the pane back
```

If the beacon never arrives, check that QEMU is running, COM1 is connected, and
the ISO is the Hermes build. The stock TinkerOS ISO does not start the daemon at
boot.
