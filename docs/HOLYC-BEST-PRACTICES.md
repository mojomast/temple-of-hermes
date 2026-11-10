# HolyC App Best Practices (TempleOS / TinkerOS / Temple of Hermes)

This guide collects the conventions used by the in-tree `Apps/` and `Demo/`
programs, the HolyC rules documented under `Doc/`, and the public TinkerOS /
TempleOS project docs. It is written for apps under `Hermes/Apps/`, starting
with the compilable skeleton in `Hermes/Apps/Template/`.

Nothing here requires a host-side HolyC compiler. HolyC is compiled by the
running OS, so the source of truth is always a boot in TempleOS or TinkerOS
(the sandbox uses TinkerOS 5.20-rc10 under QEMU TCG).

## Sources

In-tree, and therefore version-matched to this branch:

- `Doc/HolyC.DD` — language rules, types, default arguments, string printing.
- `Doc/HelloWorld.DD` — the smallest compile-and-run examples.
- `Doc/CmdLineOverview.DD`, `Doc/CompilerOverview.DD` — command line and
  compiler overview.
- `Doc/GuideLines.DD` — style and source-tree guidance.
- `Doc/Tips.DD` — editor, compile, and window-manager shortcuts.
- `Doc/DolDocOverview.DD`, `Demo/DolDoc/*.HC` — DolDoc and widget examples.
- `Apps/Chess/Load.HC`, `Apps/Chess/Run.HC` — the canonical
  `Load.HC` / `Run.HC` pair.
- `Apps/Cube/Run.HC`, `Apps/Sudoku/Run.HC`, `Apps/Wordle/Load.HC` — more
  examples of the same split.
- `Demo/Templates/*.HC` — small, focused HolyC templates.
- `Demo/HelloWorld` examples are embedded in `Doc/HelloWorld.DD`.

Public project docs (verified reachable; linked, not quoted):

- TinkerOS: <https://github.com/tinkeros/TinkerOS>
- TinkerOS releases (TinkerOS 5.20-rc10 ISO and USB image):
  <https://github.com/tinkeros/TinkerOS/releases/tag/5.20-rc10>
- TinkerOS Linux/QEMU setup:
  <https://github.com/tinkeros/TinkerOS/blob/main/LinuxQEMU.md>
- TempleOS / TinkerOS documentation portal: <https://tinkeros.github.io/>
- TempleOS downloads: <https://tinkeros.github.io/WbTempleOS/Downloads/>
- TempleOS project home: <https://templeos.org/>

## 1. Use the `Load.HC` / `Run.HC` split

Every non-trivial in-tree app follows this shape:

```text
Apps/Chess/
  Chess.HC      implementation / public routines
  Load.HC       includes the implementation, sets help index
  Run.HC        includes Load.HC and launches the app
```

`Apps/Chess/Load.HC` is the smallest useful example:

```holyc
#help_index "Games"

Cd(__DIR__);;
#include "Chess"

#help_index ""
```

`Apps/Chess/Run.HC` then launches it:

```holyc
Cd(__DIR__);;
#include "Load"
Chess;
```

Rules that follow from those examples:

- `Cd(__DIR__);;` first. It makes includes and file I/O relative to the app
  directory instead of the caller's current directory.
- `Load.HC` should only define code. It must be safe to include more than once
  and from another program. Do not open windows, prompt, or start a game in
  `Load.HC`.
- `Run.HC` is the only file with top-level side effects: it includes `Load` and
  calls the entry point.
- `#include "Name"` resolves a sibling `Name.HC`; the `#include "Load"` in
  `Run.HC` finds `Load.HC` in the same directory after `Cd(__DIR__)`.
- Use `#help_index "Category"` around public material and reset it with
  `#help_index ""` before the end of the file.
- Put shared helpers in the app's implementation file, not in `Run.HC`.
- Keep directory and file names stable; TinkerOS paths are case-sensitive in
  practice and apps are usually referenced by exactly these names.

## 2. HolyC facts worth remembering

From `Doc/HolyC.DD` and the examples in `Demo/`:

- There is no `main()`. **Any code outside a function runs when the file is
  compiled/included, in order.** That is why `Run.HC` ends with a bare call.
- Types are `I0/I8/I16/I32/I64`, `U0/U8/U16/U32/U64`, and `F64`. `U0` is the
  zero-size void type; there is no `F32`.
- A function with no arguments, or only default arguments, can be called
  without parentheses: `Dir;` is the same as `Dir()`.
- A bare string is sent to `Print`; a bare character is sent to `PutChars`.
  `"Hello\n";` and `'*';` are valid statements.
- Formatting uses `Print`-style arguments: `"x=%d name=%s\n", x, name;`.
- An empty string literal means “the next argument is the format string”:
  `"" fmt, arg;`.
- Default arguments may appear before required ones. See `Doc/HolyC.DD` for the
  exact examples.
- Variadic functions can read `argc` and `argv[]`.
- Ranges such as `0 <= i < 10` are allowed where a conjunction is obvious.
- `switch` always uses a jump table; ranges and consecutive cases are allowed.
- `//` comments are used throughout the tree.
- Preprocessor directives (`#include`, `#define`, `#help_index`,
  `#exe { ... }`) are line-oriented; `#include "Load"` needs no semicolon.

## 3. Start from the template

`Hermes/Apps/Template/` is deliberately small:

`Load.HC`

```holyc
#help_index "Hermes/Apps"
Cd(__DIR__);;

U0 HermesTemplateMain()
{
  "THE TEMPLE OF HERMES - HolyC app template\n";
  "Load.HC compiled; Run.HC launched it.\n";
}

#help_index ""
```

`Run.HC`

```holyc
Cd(__DIR__);;
#include "Load"

HermesTemplateMain;
```

Copy the directory, rename the entry point, and keep the split:

1. Rename `HermesTemplateMain` to a name that describes the app.
2. Put reusable routines and data in `Load.HC` (or in an implementation file
   that `Load.HC` includes).
3. Leave `Run.HC` as a two-step launcher: include `Load`, then call the entry
   point.
4. Add a `#help_index` category that matches the existing conventions
   (`"Games"`, `"Demos"`, `"Hermes/Apps"`, …).
5. If the app opens a window, save and restore the current dir, and return to
   the shell cleanly when the user closes the window.

## 4. Compiling and running inside the guest

The authoritative loop is the one in `Doc/HelloWorld.DD`: open the file in the
editor, press **F5**, and the OS compiles and runs it. From the command line,
the equivalent for an app pair is:

```holyc
#include "C:/Hermes/Apps/Template/Run.HC";
```

Because `Run.HC` does `Cd(__DIR__);; #include "Load"`, the launcher works no
matter which directory you were in. The template prints:

```text
THE TEMPLE OF HERMES - HolyC app template
Load.HC compiled; Run.HC launched it.
```

For a headless sandbox, TinkerOS 5.20-rc10 can be booted with QEMU TCG:

```sh
qemu-system-x86_64 \
  -accel tcg -machine pc,kernel-irqchip=off -cpu qemu64 \
  -m 2G -smp 1 -vga std -display none -nic none \
  -cdrom TinkerOS_5.20-rc10.ISO
```

Use QMP `screendump` for PNG evidence (see
`shots/hermes-holyc-guide/`). Keep disk images and ISOs outside the repo.

## 5. Error and warning policy

- Treat any compiler error as a failed build; TinkerOS reports the file and
  line in the task window.
- Fix warnings where practical. The common ones in small apps are an unused
  argument or variable; `Demo/` shows `no_warn` for intentional cases.
- Do not leave a half-open window or a task running after a compile error.
- Check the file actually exists before chasing a language error:
  `Dir("C:/Hermes/Apps/Template");` from the shell is a fast sanity check.
- A missing `#include` target produces a “file not found” error; verify
  `Cd(__DIR__);;` is the first statement in both files.
- Prefer small functions and short compile cycles; TCG builds are slower than
  KVM.

## 6. Windows, DolDoc, and user interaction

- The command line is a DolDoc document; `DocClear`, `DocBottom`, and
  `DocPrint` are the normal tools when an app needs to write text.
- Widgets and forms are demonstrated in `Demo/DolDoc/Form.HC`,
  `Demo/DolDoc/TextDemo.HC`, and `Demo/DolDoc/TreeDemo.HC`. Use those as
  working references rather than inventing a new widget protocol.
- For graphical apps, follow the examples in `Demo/Graphics/` and the
  `CSprite` / `CDC` code in `Adam/Gr/`. Save the caller's dir before changing
  it and avoid drawing outside the window.
- If an app prompts, make the prompt explicit and handle both answers. Keep
  destructive operations (format/install) out of ordinary apps.
- Leave the window manager responsive: long loops must call `Yield` or
  `Sleep`.

## 7. Testing checklist

Before considering a `Hermes/Apps/` change done:

- [ ] `Load.HC` compiles on its own (`#include "…/Load.HC";`).
- [ ] `Run.HC` compiles and launches the app.
- [ ] Running `Run.HC` a second time works (no one-shot state that breaks).
- [ ] The app returns to a usable command line after exit.
- [ ] `Cd(__DIR__);;` is present in both files.
- [ ] No absolute host-specific paths (sandbox home, workspace, or Windows
      user-profile paths) appear in source.
- [ ] Files are plain ASCII/Latin-1; no UTF-8 BOM.
- [ ] Any screenshot or log saved for review is under `shots/`, not the source
      tree.
- [ ] The app does not modify `Common/`, `Once.HC`, `Adam/Hermes/`, or
      `Hermes/Art/`.

## 8. Evidence for this template

`shots/hermes-holyc-guide/` contains the QEMU TCG screenshots from the sandbox
run:

- `01-installed-c-prompt.png` — the guest shell after installing TinkerOS
  5.20-rc10 to the virtual disk.
- `03-include-command.png` — the `#include "C:/Hermes/Apps/Template/Run"`
  command on the command line.
- `04-compiled-and-ran.png` — the template banner printed by
  `HermesTemplateMain`, followed by `Dir` showing `Load.HC` and `Run.HC`.

The ISO used for the run was the public TinkerOS 5.20-rc10 release; its
SHA-256 is recorded here for reproducibility:

```text
feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4
```

## 9. License and upstream

TempleOS is public domain by Terry A. Davis. TinkerOS is public domain under
the Unlicense. Keep the existing notices; this guide does not relicense any
upstream work.
