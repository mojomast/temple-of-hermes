# Changelog

## 0.1.3 — Temple of Hermes

### Guest
- HermesDaemon 0.1.3: HRPC file operations return structured errors (bad path,
  missing directory, read-only path, size limits) and keep answering `ping`
  instead of dropping into the debugger.
- `Adam/Hermes/Home.HC`: per-user home at `<drv>:/Home/<handle>/` with
  `JOURNAL.TXT`, `PROJECTS.TXT` and `Src/`, handle and drive validation, and
  HolyC journal helpers. Loaded at boot from `Adam/Hermes/Load.HC`.
- Boot, launcher and startup banners read v0.1.3.

### Preinstalled disk image
- `scripts/build_disk_image.py` installs the release ISO with its own
  `OSInstall.HC` into a compressed qcow2 (MBR + FAT32, writable `C:`,
  `C:/Home` and `C:/Hermes/Apps/HermesBBS` precreated) that boots to the
  launcher with no CD. `TempleOfHermes-0.1.3-disk.qcow2` ships with this
  release; it supersedes the `disk-image-0.1.3-preview` prerelease (0.1.2 base).

### BBS server (HBBS/1)
- Community extension: per-account digest, `@mention` records, `holyc` board
  download action with public server-side download counts, `challenge:<tag>`
  tags and gallery, sysop-only challenge draft approval (no cron, no
  auto-post), public reply/download counters.
- Contract section 14 now allows additive extensions (optional fields, new
  actions on existing commands, new error codes) without a version bump; the
  community features are documented as additive extensions in section 17.
- Sign-up defaults to `auto` (inline approval with the same validation,
  rate-limit and ban checks); `open` (moderated) and `closed` remain available
  via `HBBS_SIGNUP_MODE`.

### Release artifacts
- `TempleOfHermes-0.1.3.ISO`: SHA-256 `fbaa3d6f0a8f9190f295e933c32cb833a61b3cb43a708309acb6c98ff51ac4fd`, 14,053,376 bytes, volume `THE_TEMPLE_OF_HERMES`. 20/20 live boots, 18/18 launcher entries, COM2 echo, 7/7 daemon file-error cases.
- `TempleOfHermes-0.1.3-disk.qcow2`: SHA-256 `d81a3c189093bd0edddad50b7a55d6582d0490204d63720e14fc5fb9d901f1aa`, 11,107,840 bytes (4 GiB virtual). 20/20 cold boots with no CD, marker persistence, HRPC writes on `C:`, home journal on `C:` surviving reboot (23/23). Evidence: `shots/hermes-release-0.1.3/VERIFY.md`.

Binaries are attached to the GitHub release only, never committed.

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
