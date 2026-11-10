# Hermes Apps

`Hermes/Apps` is the small application layer that sits on top of the
Temple of Hermes desktop.  It is deliberately split into a data registry,
reusable helpers, and a launcher window so the same app list drives both
the launcher and the `PersonalMenu.DD` pop-up menu.

## Layout

```
Hermes/Apps/
  Registry.HC          app table: id, title, icon, description, run path, planned
  Common/
    Paths.HC           find a file under ::/Hermes, T:/Hermes, C:/Hermes or ~/Hermes
    Icons.HC           load Art/Icons/<size>/<name>.GR as a CDC
  HermesBBS/
    Load.HC            includes the real Hermes/Net sources and this app
    Core.HC            HBBS/1 framing, JSON helpers, redaction, result files
    Commands.HC        non-interactive CLI (List/Read/Post/Reply/Mail)
    UI.HC              human DolDoc board/thread/read window
    Run.HC             launcher entry point
    README.md          protocol, CLI, token, and result-file notes
  Launcher/
    Load.HC            launcher state, drawing, click/key handling, entry points
    Run.HC             Cd(__DIR__); #include "Load"; HermesAppsLauncher;
  README.md
```

The icons are the existing, checked-in art under
`Hermes/Art/Icons/{16,32,64}`.  Nothing in this directory regenerates or
duplicates the art binaries.

## Registry

`Registry.HC` defines `CHermesApp` and the `hermes_apps[]` table.  Each row is:

| Field | Meaning |
| --- | --- |
| `id` | Stable id used by `HermesAppsOpen()` and the menu |
| `title` | Label drawn under the icon |
| `icon` | Stem under `Art/Icons/32` (launcher) and `Art/Icons/16` (menu) |
| `desc` | One-line description shown in the status bar |
| `run` | Future `Run.HC` path; `NULL` for the home/about panels |
| `planned` | `TRUE` means the app is a placeholder in this change |

The current table registers `home-temple`, `hermes-bbs`, `hermes-chat`,
`worldsim`, `codex-of-nous`, `psyche`, `capybara-pet`, `messenger-run`,
`modem-net` and `nous-girl`.  The BBS entry is implemented in
`Hermes/Apps/HermesBBS` and uses the existing `modem-net` icon; it is not a
placeholder.  The six app implementations called out as out of scope
(Hermes Chat, WorldSim, Codex, Psyche, Capybara, Messenger Run) remain
`planned` entries: selecting one shows a "planned but not implemented yet"
status instead of running anything.  No `Run.HC` for those apps is
shipped here.

## Launcher

`Launcher/Run.HC` is the one-line entry point used by `Once.HC` and by
command-line users:

```holyc
Cd(__DIR__);;
#include "Load"
HermesAppsLauncher;
```

`HermesAppsLauncher()` spawns `HermesAppsLauncherTask` in its own window.
The task:

1. Loads every `Art/Icons/32/<icon>.GR` through `HermesAppsIcon()`.
2. Draws a 3-column grid with the icon, title, a selection border, and a
   footer that reports `Art icons: N/9` (proof the real Art files loaded).
3. Handles left-clicks and the keys `1`-`9`; `Enter` re-selects, `Esc`
   closes the launcher.
4. Shows the registry description, or the planned/launching status, in
   the bottom line.

If an icon is missing the launcher falls back to a labelled grey tile and
the footer count drops, so a missing overlay is visible rather than a
crash.  `HermesAppsIcon()` also retries the basename in upper case, which
covers FAT 8.3 entries that were written without a long-name record.  If
a future app's `run` path exists, the launcher spawns
`HermesAppsRunFile()` to `ExeFile` it in its own task; today those paths
do not exist.

`HermesAppsOpen(id)` is the menu-friendly entry point.  It opens the
launcher with the matching row selected.

## Autostart

`Once.HC` keeps its existing welcome text and, after printing it, calls
`HermesStartApps()`.  That helper looks for
`Hermes/Apps/Launcher/Run.HC` under `::`, `T:`, `C:` and `~/`, and
`ExeFile`s it if present.  The launcher therefore opens on the first
terminal's desktop at boot without replacing or shortening the welcome
text.  If the tree is not on the current image, the helper does nothing.

The distro should include the `Hermes` tree (`Hermes/Apps` and
`Hermes/Art`) next to `Apps`, `Adam`, `Home`, and the other top-level
directories.  The launcher also searches `T:/Hermes`, `C:/Hermes` and
`~/Hermes`, which makes a live CD, an installed disk, and a serial-pushed
overlay all work with the same source.

## PersonalMenu

`PersonalMenu.DD` has a `Temple of Hermes` section at the end.  Each
`$SP+PU` row uses a 16x16 bitmap sprite embedded in the document's
binary bins, generated from the body of `Hermes/Art/Icons/16/*.GR`, and
runs:

```holyc
HermesAppsOpen("<id>");
```

The sprites use the packed `CSprite` layout used by this TinkerOS build
(`U8 type`, then `I32 x1,y1,width,height`, then the body, then
`SPT_END`; no padding after the type byte).  The raw `.SP` files under
`Hermes/Art/Icons/16` carry three pad bytes after the type and are not
used for the menu bins.  The menu entries use the same ids and art as
the launcher.  The sprites are embedded in the document, so opening the
menu does not require the icon files to be on the current drive; the
launcher window still loads the 32x32 `.GR` files for its larger grid.
The menu macros assume the Once autostart has loaded the launcher
library, so `HermesAppsOpen()` is already defined.

## Building and testing

The launcher is plain HolyC and needs no host build step.  On a running
Temple of Hermes/TinkerOS guest:

```holyc
ExeFile("::/Hermes/Apps/Launcher/Run.HC");
```

or simply let `Once.HC` autostart it.  For the sandbox verification used
here, the guest is booted from the public TinkerOS 5.20-rc10 ISO under
QEMU TCG:

```
-accel tcg -display none -nic none -machine pc,kernel-irqchip=off
```

The source and art are pushed to `T:/Hermes/...` over COM1, then
`Once.HC` is executed.  QMP `screendump` PNGs are written to
`shots/hermes-apps/`.  The footer text `Art icons: 9/9` and the icon grid
in those shots are the acceptance evidence.

## Non-goals

This change does not implement Hermes Chat, WorldSim, Codex, Psyche,
Capybara, Messenger Run, or a template app, and does not touch
`Adam/Hermes`, `Hermes/Net`, `Hermes/Lore`, or any `Hermes/Art` binary.
