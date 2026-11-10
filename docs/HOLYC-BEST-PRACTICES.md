# HolyC best practices on THE TEMPLE OF HERMES

THE TEMPLE OF HERMES inherits the TempleOS/TinkerOS HolyC environment: one
ring-0 address space, a JIT/AOT compiler, DolDoc help, and a task per window.
This note collects habits that keep agent and human edits predictable on this
image.

## Before you edit

- Read the relevant `Doc/*.DD` page; the help system is the API reference. Start
  at `Doc/HelpIndex.DD`, then the function index or the `#help_index` on the
  source file.
- Find the include chain before changing a file. Kernel code is listed in
  `Kernel/Kernel.PRJ`; Adam startup is `StartOS.HC`; the user path is
  `MakeHome.HC` -> `HomeSys.HC` (installed in `/Home`).
- Do not edit leased paths from this workstream (Hermes apps, networking, lore,
  `Adam/Hermes/MakeDistro.HC`). Change docs or a non-leased file instead.
- Keep line endings and DolDoc dollar escapes intact. `.DD` files are not plain
  Markdown; `$...$` commands and `$$` escapes are significant.

## Writing HolyC

- Prefer the existing TempleOS idioms (`U0`, `I64`, `Bool`, `CAlloc`, `Free`,
  `StrPrint`, `MStrPrint`) over C library habits.
- Declare a function before its first use, or keep helpers above callers, as the
  existing files do.
- Do not add comments unless the surrounding file already uses them for that
  kind of explanation. The codebase is comment-light by design.
- For temporary strings use `MStrPrint` and free them; for persistent strings
  use `AStrNew` and keep ownership clear.
- A task has one window; use `DocPrint`, `DocPutS`, or plain `"..."` output
  rather than inventing a child-window model.
- The compiler is not a modern C compiler. Avoid implicit narrowing and
  declarations that depend on a later definition.

## Running and testing

- Use the command line for short checks: `6*7;`, `Dir;`, `Cd(...);`.
- Use `#include "file"` to compile a source file into the current task. Use
  `ExeFile` / `AdamFile` when the file is meant to load into Adam.
- Capture output as text where possible. On an agent-driven image, `eval` over
  the Hermes serial daemon returns stdout and errors without a screenshot.
- Compile errors emit a `compile_error` event. Fix the first error first; later
  errors are often cascades.
- Do not test destructive disk operations in a shared VM. `Fmt`, `OSInstall`,
  and `BootHDIns` are blocked in AGENT mode on purpose; use USER mode only when
  the human intends the operation.

## Kernel and startup changes

- A kernel change needs a rebuild through `BootHDIns`/`BootDVDIns`; the official
  Hermes image is produced by `scripts/build_iso.py`, not by copying a symbol
  into a stock ISO.
- `sys_os_version` is a TempleOS-family compatibility value (5.200 on this
  base). Do not repurpose it for the fork's 0.1.0 marketing version; print the
  fork version separately in banners.
- Startup order matters: `HomeSys.HC` (installed in `/Home`) creates the USER tasks, then
  `XTalk`s `Once`. The Hermes daemon is loaded from `Home/MakeHome.HC` before
  the user startup runs. Keep new autostart code in the right layer.

## Documentation and attribution

- Rebrand prose belongs in the README, `docs/`, or the relevant `Doc/*.DD` page.
- Keep the TempleOS (Terry A. Davis) and TinkerOS credit lines. They are part of
  the license and the project's history.
- Mark new in-world flavor text **NEW**. Do not invent lore; cite a source.
