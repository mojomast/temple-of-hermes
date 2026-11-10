# THE TEMPLE OF HERMES

THE TEMPLE OF HERMES is a public-domain TempleOS-family operating system built
so a human and an AI agent can share one machine without guessing what is on
screen. It is a rebrand and continuation of
[TinkerOS](https://github.com/tinkeros/TinkerOS) 5.20-rc10, which is itself a
fork of [TempleOS](https://templeos.org/) by Terry A. Davis.

- **Branch:** `hermes/rebrand`
- **Base:** `origin/hermes/art` at `97d7ad2`
- **Image version:** 0.1.0
- **License:** Unlicense / public domain (see [LICENSE](LICENSE))
- **Guest daemon version:** `Adam/Hermes/VERSION` (0.1.0)

TempleOS is the work of **Terry A. Davis** and remains public domain. TinkerOS
is the work of its authors and is released under the Unlicense. This fork keeps
those notices, keeps the Unlicense, and adds the Hermes branding, art,
agent-facing tooling, and co-use features described below. It is not affiliated
with Terry's estate, the TinkerOS authors, or Nous Research.

> New prose in this repository is documentation, not canon. Any new in-world
> flavor text is explicitly labelled **NEW**; existing lore is never rewritten
> here. See [Lore and sources](#lore-and-sources).

## What ships in this branch

### Boot, banner, and launcher surface

The live image boots straight to a usable USER session instead of stopping at
the first-boot install and tour prompts. The startup text, the Start document,
the About page, and the debugger banner all read **THE TEMPLE OF HERMES** and
show version 0.1.0.

The first terminal is the launcher surface in this branch:

- `Once.HC` prints the welcome, the version, the serial-channel summary, and the
  install note.
- `HomeSys.HC` (installed as `/Home/HomeSys.HC`) creates the first USER task and opens `Doc/Start.DD`.
- `Doc/Start.DD` is the title page and quick index for Help, the command line,
  and the agent guide.
- `OSInstall` is still available, but it is not run automatically. In AGENT
  mode the input gate refuses install and format operations.

A graphical application launcher is a companion workstream, not a shipped
binary in this tree. The icons and visual language for it are already in
`Hermes/Art/Icons/` (see [docs/ART.md](docs/ART.md)).

### Applications

The stock TinkerOS application set remains in `Apps/`, including After Egypt,
Chess, CF2, Cube, Oregon Trail, Sudoku, Wordle, SpyHunt, and the demo suite.
The template also carries the Hermes companion app identities used by the art
set: `hermes-chat`, `worldsim`, `codex-of-nous`, `psyche`, `capybara-pet`,
`messenger-run`, `modem-net`, and `home-temple`. Those app sources live in
their own leased workstreams; this branch ships their art and documentation,
not their implementation.

### Art

`Hermes/Art/` contains the OS-facing wallpaper, boot splash, icons, sprites,
and UI strips, plus the pure-Python converters and palette reference. The
assets use only the exact TempleOS 16-colour `gr32_palette_std` palette unless a
document says otherwise. See [docs/ART.md](docs/ART.md) for the full manifest,
the `.GR` / `.SP` formats, and regeneration commands.

### Hayes-style modem networking (planned workstream)

The networking direction is a Hayes-compatible modem bridge: an AT-command
serial channel that lets the guest dial, answer, and exchange text without
requiring a modern TCP/IP stack in ring 0. This is **planned**; the source is in
the leased `Hermes/Net/` workstream and is not present in this tree. The
`modem-net` icon in `Hermes/Art/Icons/` is a visual placeholder for that work.
Do not treat this section as a claim that AT dialing already works.

### Hermes Chat (companion app, leased workstream)

Hermes Chat is the human/agent conversation app for the image. Its source is
owned by the `Hermes/Apps/HermesChat/` workstream and is not edited here. This
branch provides the `hermes-chat` icon family and documents the interface
expectations for the agent tools. The serial daemon described below is the
ground-truth channel the chat app and plugins use.

### Lore and sources

Lore is owned by a separate workstream and is not authored or rewritten in this
branch. If lore is mentioned anywhere in this tree, the source must be cited.
The art guide already states the rule: "Lore lines that appear in other branches
must stay sourced." See [docs/ART.md](docs/ART.md) and the upstream TempleOS
documentation under `Doc/`. New in-world text added by this rebrand must be
marked **NEW**.

### Agent tools and the serial channel

The `hermes-templeos` plugin drives the guest through four tools:

| Tool | Purpose |
| --- | --- |
| `templeos_vm` | Start/stop/status the Hermes QEMU machine and surface the beacon. |
| `templeos_screen` | Prefer ground-truth `text` over screenshots; read or hash the screen when needed. |
| `templeos_input` | Type, send keys, click, move, and evaluate HolyC; keep the agent cursor in sync. |
| `templeos_files` | List, pull, and push files through the guest daemon. |

The guest daemon (`Adam/Hermes/`) listens on COM1 at 115200 8n1 and speaks
length-prefixed ASCII frames:

```text
HBEACON TempleOfHermes/0.1.0
HREQ <id> <op> <len>\n + <len bytes of payload>
HRPL <id> <ok|err> <len>\n + <len bytes>
HEVT <seq> <kind> <len>\n + <len bytes of JSON>
```

If your agent workflow is new to this image, read
[docs/USING-WITH-HERMES-AGENTS.md](docs/USING-WITH-HERMES-AGENTS.md) first. It
covers the four plugin tools, low-token habits, the serial channel, and launcher
autostart.

### Presence, modes, and safety guards

The guest has three modes: **USER**, **SHARED**, and **AGENT**. The wallpaper
banner shows which mode is active, and in SHARED or AGENT mode a second cyan /
yellow crosshair marks the agent's pointer. In AGENT mode the kernel input gate
refuses `YorN`, `AreYouSure`, `Fmt`, `OSInstall`, and `BootHDIns`, and emits a
`danger_blocked` event. SHARED still lets a human answer an ordinary `YorN`, but
format and install remain blocked.

## Build the image

The builder follows TinkerOS's own distro path (`BootDVDIns` + `RedSeaISO`).
QEMU and a TinkerOS 5.20-rc10 ISO are required. Networking stays off. In this
sandbox there is no usable KVM, so TCG is the expected path.

```bash
python3 scripts/build_iso.py
# writes dist/TempleOfHermes-0.1.0.ISO and dist/SHA256SUMS

python3 scripts/smoke.py
# screenshots and serial transcript under shots/
```

The upstream ISO, if you need to fetch it, is TinkerOS 5.20-rc10 with SHA-256
`feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4`.
Verify the hash before using it.

## Documentation map

| Document | Contents |
| --- | --- |
| [docs/USING-WITH-HERMES-AGENTS.md](docs/USING-WITH-HERMES-AGENTS.md) | Efficient agent workflow, the four plugin tools, serial channel, autostart. |
| [docs/REBRAND.md](docs/REBRAND.md) | Canonical names, version strings, attribution rules, and the deferred ISO label request. |
| [docs/HERMES-FEATURES.md](docs/HERMES-FEATURES.md) | Protocol, research, prior art, and feature rationale. |
| [docs/ART.md](docs/ART.md) | Art manifest, palette, formats, and converter usage. |
| [docs/HOLYC-BEST-PRACTICES.md](docs/HOLYC-BEST-PRACTICES.md) | Working in HolyC on this image. |
| [docs/QEMU-SANDBOX-PROBE.md](docs/QEMU-SANDBOX-PROBE.md) | TCG-only QEMU recipe and boot probe. |
| [docs/upstream/](docs/upstream/) | Preserved TinkerOS-focused documentation, with provenance notes. |
| [PLUGIN-INTEGRATION.md](PLUGIN-INTEGRATION.md) | How the plugin maps the daemon onto four tools. |

## Credits and license

- **Terry A. Davis** created TempleOS, HolyC, DolDoc, and RedSea. TempleOS is
  public domain.
- **The TinkerOS authors** maintain the TempleOS-compatible base and the VM
  installer used here. TinkerOS is released under the Unlicense.
- **ZealOS** supplied code that TinkerOS already credits.
- **Spirit** (und3f/temple-os-apps) is the closest prior art for a boot-time
  serial guest agent; its idea is credited in
  [docs/HERMES-FEATURES.md](docs/HERMES-FEATURES.md).

See [LICENSE](LICENSE) and [CREDITS.md](CREDITS.md). The Hermes daemon, exact
text export, presence banner, event stream, skip-install boot, branding, art,
and agent-aware guards are new in this fork and are also placed in the public
domain under the Unlicense.

## ISO label request

The distro ISO volume/label string is intentionally **not** applied in this
branch. `Adam/Hermes/MakeDistro.HC` is owned by the TOH-INT workstream. The
exact requested label and the integration note are in
[docs/REBRAND.md](docs/REBRAND.md#iso-label-request-for-toh-int).
