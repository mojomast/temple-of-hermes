# THE TEMPLE OF HERMES rebrand notes

This file records the naming rules, the user-visible strings, the attribution
requirements, and the one deferred distro-label change. It applies to branch
`hermes/rebrand`, based on `origin/hermes/art` at `97d7ad2`.

## Canonical names

| Kind | Value |
| --- | --- |
| Product name | **THE TEMPLE OF HERMES** |
| Short name | **Temple of Hermes** |
| Image / host artifact | `TempleOfHermes-0.1.0.ISO` |
| Image version | `0.1.0` |
| Guest daemon beacon | `HBEACON TempleOfHermes/0.1.0` |
| Base OS / compatibility name | TinkerOS 5.20-rc10 |
| Upstream OS / lineage | TempleOS by Terry A. Davis |

The all-caps form is used for boot, banner, About, and Start-page titles. The
mixed-case form is used in ordinary prose and filenames.

## Version strings

- The Temple of Hermes release is **0.1.0**.
- `sys_os_version` stays `5.200` because it is a TinkerOS compatibility value
  used by existing TempleOS-family code. Do not change it just to display a new
  marketing version.
- Banners that face the user show both the fork version and the base, for
  example: `THE TEMPLE OF HERMES 0.1.0 (TinkerOS 5.200 base)`.
- `Adam/Hermes/VERSION` contains `0.1.0` and is the daemon's source of truth.

## User-visible strings changed in this branch

| Location | What the user sees |
| --- | --- |
| `Kernel/KMain.HC` | Boot banner: `THE TEMPLE OF HERMES 0.1.0 (TinkerOS V<base> base)`. |
| `Kernel/KDbg.HC` | Fault/debug banner: `THE TEMPLE OF HERMES Debugger`. |
| `Once.HC` | Welcome, version, serial summary, install note, and credit line. |
| `Doc/Start.DD` | Start-page title: `THE TEMPLE OF HERMES`; links to About and Help. |
| `Doc/AboutHermes.DD` | New About page for THE TEMPLE OF HERMES with attribution. |
| `Doc/HelpIndex.DD` | Help index labels the fork's page and marks TinkerOS material as upstream. |
| `Doc/Features.DD` | Fork feature list, with a pointer to upstream TempleOS/TinkerOS features. |
| `Doc/Welcome.DD` | Welcome page names THE TEMPLE OF HERMES and the upstream lineage. |
| `Doc/Install.DD` | Install page names THE TEMPLE OF HERMES while keeping the TempleOS/TinkerOS paths. |
| `Doc/Requirements.DD` | Requirements page names THE TEMPLE OF HERMES and the TinkerOS base. |
| `Misc/OSInstall.HC` | Installer prompts name THE TEMPLE OF HERMES while crediting the base. |
| `Kernel/BlkDev/FileSysFAT.HC`, `Kernel/BlkDev/FileSysRedSea.HC` | Newly formatted volume names use the short `TEMPLE` prefix (FAT label length limit). |

TinkerOS mentions that describe upstream history, upstream URLs, API names, or
tour content are intentionally preserved. Removing them would erase the
attribution that the license and the project require.

## Attribution and licenses

Every rebranded surface keeps a clear line to both upstreams:

- **TempleOS** — created by **Terry A. Davis**; public domain.
- **TinkerOS** — the TempleOS-compatible base (`tinkeros/TinkerOS` 5.20-rc10);
  released under the Unlicense.
- **ZealOS** — credited by TinkerOS for ported code.
- **Spirit** — credited as prior art for a boot-time serial guest agent.

`LICENSE` remains the Unlicense. `CREDITS.md`, `Doc/Credits.DD`,
`Doc/AboutTempleOS.DD`, and `Doc/AboutTinkerOS.DD` remain available. The new
`Doc/AboutHermes.DD` links to them rather than replacing them.

## Lore rule

Lore is owned by a separate workstream. This branch does not invent, rewrite, or
retcon lore. If a document needs to mention lore, it must cite a source. New
in-world flavor text is allowed only when it is explicitly marked **NEW**.

## Art rule

The rebrand uses the existing `Hermes/Art/` assets. Symbolic motifs (caduceus,
temple facade, talaria, 16-colour dither) are original art, not historical
claims. See `docs/ART.md`.

## ISO label request for TOH-INT

**Status: requested only. Not applied in `hermes/rebrand`.**

`Adam/Hermes/MakeDistro.HC` is owned by the TOH-INT workstream, so this branch
does not edit it. Please apply exactly this label when the distro is built:

```text
THE_TEMPLE_OF_HERMES
```

That is the requested ISO 9660 **Volume Identifier** string (20 characters,
uppercase A–Z and underscore only). It fits the 32-character ISO 9660 Volume
Identifier field and the common 32-character volume-label limit. Please use it
verbatim, without appending a version, so the media label stays stable across
0.1.x builds. The version belongs in the filename and the boot banner, not in
the volume label.

If the build path also writes the El Torito boot-catalog identifier, use the
same string `THE_TEMPLE_OF_HERMES` there as well. If the boot catalog rejects
underscores in that field, leave the boot-catalog identifier unchanged rather
than inventing a second product label.

Current state of the relevant source, for INT's reference only:

- `Adam/Opt/Boot/DskISORedSea.HC` currently writes a publisher id
  (`TempleOS RedSea`) and an El Torito id; the ISO9660 Volume Identifier is the
  field to set.
- No label change is made in this branch, and no generated ISO is committed.

## What this branch deliberately does not do

- It does not merge, tag, or force-push `hermes/v0` or `main`.
- It does not edit leased paths, including `Adam/Hermes/MakeDistro.HC`.
- It does not build a BBS or any agent-to-agent message board. That idea is
  still under research and is out of scope.
- It does not delete legacy TinkerOS documentation. Copies are preserved under
  `docs/upstream/`, and the in-OS help files remain in `Doc/`.
