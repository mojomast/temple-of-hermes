# Plugin integration handoff

This file is for the hermes-templeos plugin (https://github.com/mojomast/hermes-templeos).
**Do not edit the plugin from this workstream.** It describes how to add a
`hermes` flavor that speaks the guest daemon, while keeping the public surface
at **four tools**.

Related: [docs/HERMES-FEATURES.md](docs/HERMES-FEATURES.md) (protocol and
research) and [docs/CONTRACTS.md](https://github.com/mojomast/hermes-templeos/blob/feat/integration/docs/CONTRACTS.md)
in the plugin (existing four-tool envelope).

## Flavor

Add a fourth flavor id, `hermes`, alongside `tinkeros`, `templeos`, and
`zealos`. Suggested pin, filled in after `scripts/build_iso.py` writes
`dist/SHA256SUMS`:

| Field | Value |
| --- | --- |
| `id` | `hermes` |
| `name` | THE TEMPLE OF HERMES 0.1.0 |
| `iso_filename` | `TempleOfHermes-0.1.0.ISO` |
| `url` | A GitHub Release of `mojomast/temple-of-hermes` once Kyle publishes one (do not invent a tag). Until then, doctor can accept a locally built ISO that matches the SHA-256. |
| `sha256` | See `dist/SHA256SUMS` after the image build. |
| `width` × `height` | 640 × 480 |
| `bus` | `ide` (same as TinkerOS) |
| `mouse` | `vmmouse` (Home/MakeHome still loads `/Demo/VM/VMMouse` under a hypervisor) |
| `serial` | `hrpc` (new strategy: the daemon is already running; do not type `CommInit`) |
| `hash_crop` | Same crop as TinkerOS is a starting point, but the bottom text row is now a presence banner and the top-left cells are a mode badge, so a slightly tighter crop (or ignoring those rows) will hash more stably. Prefer events/`idle` over hashes. |

QEMU flags stay the proven TinkerOS ones: `-machine pc,kernel-irqchip=off`,
`-cpu qemu64`, `-m 2G`, `-smp 1`, `-vga std`, `-nic none`, QMP / VNC / COM1 on
unix sockets, IDE CD + qcow2. Networking stays off. The box this image was
built on has no usable `/dev/kvm`; TCG works, KVM should work when `/dev/kvm`
opens.

Default flavor can stay `tinkeros` until the ISO is published and the smoke
test is green; then consider defaulting new installs to `hermes`.

## Keep four tools

Do not add `templeos_daemon` or a fifth tool. Map the new RPCs onto the
existing ops and JSON envelope. Schema token count should stay flat: new
optional fields on existing ops, or a `via` hint, not new tool names.

| Tool | Op | Hermes flavor behavior |
| --- | --- | --- |
| `templeos_vm` | `start` | Boot the Hermes ISO. Open COM1 immediately and wait (timeout ~few minutes under TCG) for `HBEACON TempleOfHermes/0.1.0`. Surface `ready: true` and `mode: user` in `status`. Do **not** type `CommInit; CommInit8n1(1,115200);` — the guest already did. |
| `templeos_vm` | `stop` `reset` `snapshot` `restore` `status` `doctor` | Unchanged host-side QEMU. `doctor` verifies the new ISO URL/SHA. `status` can add `hermes: {beacon, mode, ready}` when the flavor is `hermes`. `snapshot` still ejects the floppy first, as in the TinkerOS bake-off. |
| `templeos_screen` | `look` `hash` | Still QMP `screendump`. The banner and clock will move hashes; use the flavor crop. |
| `templeos_screen` | `read_text` | **Prefer `text` RPC** (`focus` by default, `all` if the caller asks for every window). Fall back to glyph OCR only if COM1 is down (`serial_not_ready`) or the reply is `err`. Return the ground-truth string, and optionally cursor + window list as already-allowed extra fields in the envelope. |
| `templeos_screen` | `wait_idle` | **Prefer `idle` + `events`**. Wait until `prompt` is 0, `evt_pending` is 0 (or only stale events), and optionally a short quiet period. Treat `prompt_waiting` and `compile_error` as *not* idle. Keep the cropped-hash fallback when serial is down. |
| `templeos_input` | `type` `keys` `click` `move` | Still QMP / VMMouse, so the user can also drive the pane. After a `move`/`click` that the agent issued, also send `mouse x,y` so the guest's agent crosshair tracks. |
| `templeos_input` | `holyc` | **Prefer `eval` RPC** (captures output and compile errors, emits `compile_error`). Fall back to the current `auto\|serial\|type` injection only if HRPC is down. |
| `templeos_input` (same tool, no new name) | mode / presence | Reuse or lightly extend this tool (or `templeos_vm` `status`) to send `mode` `user\|shared\|agent`. Wire it to the host arbiter: when the pane is in "You drive", send `user`; when the agent is about to act, send `agent`; shared stays `shared`. Do not add a fifth tool for this. |
| `templeos_files` | `list` `pull` `push` | **Prefer HRPC `list` / `pull` / `push`**. The daemon talks the same ideas as `Xfer.HC` (TXFR) but with HRPC framing, already running, no need to inject `Xfer.HC`. Keep the TXFR path for stock `tinkeros`. `pull` replies with raw bytes in the HRPC payload. |

## Arbiter and the guest banner

The plugin already has watch / shared / user with a ~2 s hold-off and
`agent_paused`. On the `hermes` flavor:

- Host `user` ↔ guest `mode user` (banner green, guards off, agent cursor hidden).
- Host `shared` ↔ guest `mode shared` (cyan banner, format/install still blocked).
- Host "agent is acting" ↔ guest `mode agent` (red/yellow banner, `YorN` blocked too).

If the host arbiter pauses the agent, set guest mode back to `user` or
`shared` so the on-screen banner matches what the pane says.

## What not to do

- Do not enable QEMU networking. The daemon is serial-only.
- Do not bundle QEMU or the ISO in the plugin (catalog rule). Doctor should
  fetch or accept a verified local ISO.
- Do not load `Xfer.HC` and HRPC on the same COM1 at the same time.
- Do not add tools. Four is the contract.
- Do not treat this file as permission to merge, tag, or publish a release of
  either repo.

## Smoke checklist the plugin can reuse

`scripts/smoke.py` in this repo already: boots the ISO, waits for `HBEACON`,
pings, dumps focus text, switches to AGENT (screenshot of the banner), moves
the agent cursor, evals `"Hello from Hermes";` and `6*7`, reads the text back,
tries `OSInstall` (expects `danger_blocked`), exercises clipboard and
`list /Adam/Hermes`, and returns to USER. A plugin live test can follow the
same sequence through the four tools instead of a raw HRPC client.
