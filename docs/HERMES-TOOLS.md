# The Temple of Hermes — tool RPC contract

This document is the additive contract for the structured tool RPCs served by
the guest daemon on **COM1**. It extends, and does not replace,
[HERMES-FEATURES.md](HERMES-FEATURES.md): all v0.1.0 operations keep their
existing names, framing, payloads, and reply shapes.

The daemon is `Adam/Hermes/Daemon.HC`, started by `Adam/Hermes/Load.HC`. The
wire encoding is still ASCII headers followed by a raw payload of exactly the
declared length. No generic JSON parser is required in the guest; replies are
emitted as a JSON subset with `"`, `\`, newline, carriage return, and tab
escaped.

## Framing (unchanged)

```
HBEACON <name>/<version>\n
HREQ <id> <op> <len>\n  + <len raw payload bytes>
HRPL <id> <ok|err> <len>\n + <len raw payload bytes>
HEVT <seq> <kind> <len>\n + <len payload bytes>
```

- `<id>` is a decimal host-chosen request id, echoed in `HRPL`.
- `<op>` is `[A-Za-z_]` and is case-insensitive in the guest.
- `<len>` is decimal, `0..262144`.
- `HEVT` frames may interleave between a request and its reply. A client must
  parse events before expecting the reply (the reference host client does).
- `err` replies carry a short ASCII reason. Existing reasons are unchanged;
  new reasons are listed with the new ops below.

## Compatibility

All original operations remain:

`ping`, `help`, `eval`, `tasks`, `focus`, `mouse`, `text`, `mode`,
`clip_get`, `clip_set`, `list`, `pull`, `push`, `events`, `idle`.

The additions below are aliases or new names. Aliases never change the old
request or reply shape:

| Existing | Added alias | Notes |
| --- | --- | --- |
| `list` | `ls` | Same path argument and same array reply, now with more fields. |
| `tasks` | `task_list` | Same structured task reply. |
| `focus` | `window_focus` | Same focus switch, but replies with the window list. |

`help` now advertises the complete op list. Consumers should treat the list as
open-ended and ignore unknown names.

## Extended `list` / `ls`

Payload: path or filesystem find mask, default `/`.
Reply: JSON array. The original `name` and `is_dir` fields are preserved; three
metadata fields are added:

```json
[
  {"name": "Hermes", "is_dir": 1, "size": 0, "attr": 16, "datetime": 0},
  {"name": "Daemon.HC", "is_dir": 0, "size": 12345, "attr": 0, "datetime": 1234567}
]
```

- `size` is the byte size reported by the filesystem.
- `attr` is the raw TinkerOS directory attribute word.
- `datetime` is the raw `CDate` timestamp integer.

## `stat`

Payload: one exact path (an empty payload means `/`).
Reply: one object. No error is raised for a missing path.

```json
{"path": "/Adam/Hermes", "exists": 1, "name": "Hermes",
 "size": 0, "attr": 16, "is_dir": 1, "datetime": 0}
{"path": "/missing", "exists": 0}
```

## Structured `eval`

Payload: raw HolyC source. Reply keeps `ok` and `text`, and gains `error`:

```json
{"ok": 1, "text": "42\n", "error": null}
```

On a compile or runtime failure:

```json
{"ok": 0, "text": "Compile Error: ... on line 3 col 7\n",
 "error": {"kind": "compile", "code": 67, "line": 3, "col": 7,
           "message": "Compile Error: ... on line 3 col 7\n"}}
```

- `kind` is `compile` (compiler or parser text), `link` (undefined extern), or
  `exception` (any other HolyC exception).
- `code` is the raw HolyC `except_ch` value when the guest caught an exception,
  otherwise `0`.
- `line` and `col` are parsed from the exception text when present, otherwise
  `0`.
- Every failure still pushes a `compile_error` event, exactly as before.

## Tasks, windows, and focus

### `tasks` / `task_list`

Unchanged shape. Each task object keeps `addr`, `name`, `title`, `win`,
`show`, and `focus`. `addr` is the printable task pointer (`"0x..."`) used by
`focus` and `task_kill`.

### `task_kill`

Payload: task address (`0x...`) or window/task title.

Reply:

```json
{"ok": 1, "killed": 1, "addr": "0x2000", "title": "Welcome"}
```

`killed` is `1` when the guest issued the termination. Errors:

- `no_task` — the payload is empty or resolves to no live task.
- `protected_task` — the daemon refuses to kill itself, Adam, or the window
  manager.

### `windows`

Payload: ignored. Reply:

```json
{"focus": "0x1000",
 "windows": [
   {"addr": "0x1000", "name": "adam", "title": "Adam",
    "win": [0, 0, 79, 59], "show": 1, "focus": 1, "z": 2,
    "cursor": {"x": 0, "y": 0, "line": 0, "col": 0}}
 ]}
```

Only visible, non-daemon, non-window-manager tasks are listed. `win` is the
text-cell rectangle `[left, top, right, bottom]`; `z` is `win_z_num`.

### `window_focus`

Payload: empty to query, or a task address/title to raise. Reply has the
`windows` shape above. `no_task` means the target did not resolve. The original
`focus` op is unchanged and returns the task list.

## DolDoc read and write

### `doc_read`

Payload: a file path. An empty payload reads the focused window's document.
Reply:

```json
{"ok": 1, "path": "/Tmp/Note.DD", "size": 27,
 "dol": "$$FG,YELLOW$$Hello$$FG$$\n", "text": "Hello\n"}
```

- `dol` is the exact DolDoc source (`DocSave`).
- `text` is the plain-text rendering (`HermesDocPlain`).
- On failure: `{"ok": 0, "error": "doc_read"}`.

### `doc_write`

Payload: `path` + one NUL byte + raw DolDoc source. Reply:

```json
{"ok": 1, "wrote": 27, "path": "/Tmp/Note.DD"}
```

Errors: `doc_path` (no NUL / path separator in the payload) and `doc_write`
(the filesystem rejected the write). Reading the file back through `doc_read`
round-trips the same DolDoc text.

## `toast`

Payload: message text. The guest displays a centered banner row near the top of
the screen for about five seconds, prefixed with `Hermes says:` unless the
caller already supplied that prefix. It also pushes a `toast` event.

Reply:

```json
{"ok": 1, "toast": "Hermes says: safe to continue", "until": 123.456}
```

`until` is the guest uptime (seconds) at which the banner expires.

## Safe-mode guard query: `guards`

Payload: optional operation name to test (`Fmt`, `AreYouSure`, `OSInstall`,
`BootHDIns`, `YorN`); default `Fmt`.

Reply:

```json
{"mode": "agent", "safe_mode": 1, "what": "Fmt", "allow": 0,
 "input_gate": 1, "guard_installed": 1,
 "blocked": ["Fmt", "AreYouSure", "OSInstall", "BootHDIns"],
 "yorn_blocked": 1}
```

- `safe_mode` is `1` outside `user` mode.
- `allow` is the pure decision the kernel gate would make for `what`; the
  query does not print the refusal notice or push an event.
- `input_gate` is `1` when a gate function is installed.
- `guard_installed` is `1` when it is the Hermes gate.
- `yorn_blocked` is `1` only in `agent` mode (`shared` still permits ordinary
  yes/no dialogs for the human).

## `sysinfo`

Payload: ignored. Reply:

```json
{"name": "TempleOfHermes", "version": "0.1.0", "os_version": 5.2,
 "t": 123.456, "time": "2026-11-09T12:34:56", "mode": "user",
 "ready": 1, "tasks": 12, "windows": 3, "tasks_spawned": 40,
 "mem_phys": 2147483648, "heap_base": "0x...", "heap_limit": "0x...",
 "screen": {"w": 640, "h": 480, "cols": 80, "rows": 60},
 "com": {"port": 1, "baud": 115200},
 "build": {"compiler": "HolyC"}}
```

`t` and `ready` are the same values used by `ping` / `idle`.

## Events

The original event kinds are unchanged:

`ready`, `task_spawned`, `window_opened`, `prompt_waiting`,
`compile_error`, `mode_changed`, `danger_blocked`.

`toast` is added for the new banner. Its `data` is the displayed text.

## Reference host client

`host/hermes_daemon_client.py` implements framing, interleaved event handling,
and typed methods for every op above. It accepts either a QEMU COM1 unix socket
or an injected transport:

```python
from host.hermes_daemon_client import HermesDaemonClient

with HermesDaemonClient("/tmp/.../com1.sock") as client:
    client.wait_beacon()
    info = client.sysinfo()
    client.toast("safe to continue")
    print(client.eval("6*7"))
    print(client.windows())
```

`host/tests/test_hermes_daemon_client.py` exercises the same code against an
in-memory fake serial port, including partial reads, interleaved `HEVT` frames,
binary `push` / `pull`, and remote `err` replies.

## Proof under QEMU TCG

`shots/hermes-tools/` contains the capture from the TCG sandbox:

- QMP `screendump` PNGs of the stock TinkerOS 5.20-rc10 live desktop, the
  live command prompt, the `CommInit8n1(1,115200)` check, and the serial
  receiver compiling and starting.
- `test-results.txt` from the host client suite.

The full custom image was assembled under TCG as well, but the guest-side
legacy `RedSeaISO` build path could not write the expanded staged tree on the
sandbox's RAM drive, so the daemon/toast screenshots from a booted Hermes image
remain an open item. The reference client and its fake-serial suite do exercise
every op above.

QEMU is always TCG in this sandbox:

```
-accel tcg -display none -nic none -machine pc,kernel-irqchip=off
```

No networking, no KVM, no merge to `main` or `hermes/v0`.
