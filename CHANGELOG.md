# Changelog

## 0.1.0 — THE TEMPLE OF HERMES (hermes/v0)

Forked from TinkerOS 5.20-rc10
([tinkeros/TinkerOS](https://github.com/tinkeros/TinkerOS) tag `5.20-rc10`,
commit `b8d1703b73fd027a35ede9b6e37ae9430e49f1bb`). License remains the
Unlicense (public domain), with credit to Terry A. Davis and the TinkerOS
authors.

### New

- Hermes agent daemon on COM1 (115200 8n1): length-prefixed `HBEACON` / `HREQ`
  / `HRPL` / `HEVT` frames. Ops: ping, eval, tasks, focus, mouse, text, mode,
  clip_get, clip_set, list, pull, push, events, idle, help.
- Exact DolDoc text export of the focused window or every visible window,
  including cursor position, over serial.
- On-screen presence banner (`THE TEMPLE OF HERMES [user|shared|agent]`) and a
  distinct agent crosshair, layered on the stock mouse arrow.
- Event stream: ready, task_spawned, window_opened, prompt_waiting,
  compile_error, mode_changed, danger_blocked.
- First boot skips the install and tour prompts, starts the daemon, prints a
  ready beacon, and brands the Start document and wallpaper.
- `fp_input_gate` kernel hook: the agent cannot confirm `YorN` / `AreYouSure`
  / `Fmt` / `OSInstall` / `BootHDIns` while mode is AGENT (SHARED still blocks
  format and install).

### Notes

- Clipboard RPCs are included for the plugin but are not a new idea: Spirit and
  TinkerOS TOSClient already moved clip text over serial.
- Host build and smoke scripts live in `scripts/`. The bootable image is
  `dist/TempleOfHermes-0.1.0.ISO`.
