# Rebrand verification notes

Branch: `hermes/rebrand` (base `hermes/art` at `97d7ad2`). These are source-level
checks; no boot screenshot was captured in this sandbox (see
`shots/hermes-rebrand/README.md`).

## Required visible strings

Command:

```bash
grep -n "THE TEMPLE OF HERMES" \
  Once.HC Kernel/KMain.HC Kernel/KDbg.HC \
  Doc/Start.DD Doc/AboutHermes.DD Doc/Welcome.DD Doc/Features.DD \
  Misc/OSInstall.HC
```

Observed:

```text
Once.HC:16:          THE TEMPLE OF HERMES  v0.1.0
Kernel/KMain.HC:154:  THE TEMPLE OF HERMES 0.1.0 (TinkerOS V%5.3f base)
Kernel/KDbg.HC:659:   THE TEMPLE OF HERMES Debugger
Doc/Start.DD:1:       THE TEMPLE OF HERMES
Doc/AboutHermes.DD:1: About THE TEMPLE OF HERMES
Doc/Welcome.DD:1:     Welcome to THE TEMPLE OF HERMES
Doc/Features.DD:1:    THE TEMPLE OF HERMES' Features
Misc/OSInstall.HC:215: Select graphics mode (THE TEMPLE OF HERMES)
```

## Old key banners removed

Command:

```bash
grep -rn "TinkerOS Debugger\|Welcome to TinkerOS\|TinkerOS' Features\|Select graphics mode (TinkerOS)\|Requirements for TinkerOS\|Installing TinkerOS" \
  Kernel Doc Misc Once.HC
```

Observed: no matches outside the historical `Doc/Baremetal/**/Survey.DD` machine
survey records, which are records of what older TinkerOS builds printed and are
kept as-is.

## Attribution and license

Command:

```bash
grep -n "Terry A. Davis" README.md Once.HC Doc/AboutHermes.DD Doc/Start.DD
```

Observed in README, Once, Start, and the About page. `LICENSE` is unchanged and
still the Unlicense. `CREDITS.md` is unchanged. `Doc/AboutTempleOS.DD`,
`Doc/AboutTinkerOS.DD`, and `Doc/Credits.DD` remain in place, and
`Doc/AboutTinkerOS.DD` links to the new About page.

## Legacy docs preserved, not deleted

`docs/upstream/` contains copies of the pre-rebrand Linux/Windows QEMU guides,
the bare-metal guide, and the TinkerOS-focused in-OS pages. The originals
remain at their old paths. See `docs/upstream/README.md`.

## Rebrand ownership boundaries

```bash
git diff --quiet -- Adam/Hermes/MakeDistro.HC && echo clean
```

Observed: clean. `MakeDistro.HC` was not edited.

No leased path was edited. The changed set is limited to `README.md`,
`Once.HC`, `Doc/`, `Kernel/`, `Misc/`, `LinuxQEMU.md`, `docs/`, and
`shots/hermes-rebrand/`.

## ISO label request

The requested label is documented in `docs/REBRAND.md` as exactly:

```text
THE_TEMPLE_OF_HERMES
```

It is a request for TOH-INT. No label change is applied in this branch.

## Out of scope

No BBS or agent-to-agent message board was built. Lore was not invented or
rewritten; the only lore statement is the sourcing rule inherited from
`docs/ART.md`.
