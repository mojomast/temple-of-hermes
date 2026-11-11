# Hermes home directory (slice B) verification

- Base: `hermes/daemon-fix-0.1.3` at `2071daa299419aa125c1a42fc2ba59a4c6b47ca2`
  (in-guest version 0.1.3).
- Work branch: `hermes/home-journal`; all changes are uncommitted in the
  worktree.
- Assigned changes: `Adam/Hermes/Home.HC`, `Adam/Hermes/HomeTest.HC`, one
  `#include "Home"` line in `Adam/Hermes/Load.HC`, `scripts/test_home_journal.py`,
  `docs/HOME-DIR.md`, and this evidence directory.

## Layout under test

```text
C:/Home/<handle>/
  JOURNAL.TXT      "YYYY-MM-DD HH:MM <text>", one per session, <=200 chars
  PROJECTS.TXT     "Current: <project>" and "Next: <next step>"
  Src/             small programs
```

`<handle>` is 1-32 of `A-Z a-z 0-9 . - _`; the default is `hermes`. `HomeInit`
creates the directories, `JournalAdd` appends and sanitises, `JournalTail`
reads the newest lines, and `ProjectSet`/`ProjectShow` write and read the two
project lines. Every helper returns an allocated `OK ...` or `ERR <code>`
string. `HomeInit` checks `DrvIsWritable`, so a missing or read-only drive is
an error string, never a debugger.

## Static / source matrix (executed)

Command: `python3 scripts/test_home_journal.py --static`

Result: **30/30 PASS** (exit 0).

| Check | Result |
| --- | --- |
| `HomeInit`, `JournalAdd`, `JournalTail`, `ProjectSet`, `ProjectShow`, `HomeDir` defined | PASS |
| Journal limit `HERMES_HOME_LINE_MAX 200` | PASS |
| `Current:` / `Next:` writer | PASS |
| `Src/` directory creation | PASS |
| `DrvIsWritable` guard and `ERR drive_not_writable` | PASS |
| Control-byte stripping | PASS |
| Guest test calls `JournalTail(3)`, `ProjectSet`, and the no-C path | PASS |
| `Load.HC` has exactly one `#include "Home"` line | PASS |
| Home/test sources have balanced `{}`/`()`/`[]` and include guards | PASS |
| Documentation covers the layout, both drive classes, and the host reader | PASS |
| Host parser accepts the contract fixture | PASS |
| Host parser rejects a tab and a >200-char line | PASS |
| Project parser accepts exactly `Current:` + `Next:` | PASS |

Logs:

- `home-journal-static.log` — static check transcript.
- `home-journal-static.json` — machine-readable static matrix.
- `home-journal.log` — the default command's prerequisite result in this
  sandbox (exit 2, no QEMU/Pillow/ISO).

## QEMU matrix (not executed in this sandbox)

Command: `python3 scripts/test_home_journal.py`

The sandbox has no `qemu-system-x86_64`, no Pillow, no v0.1.2 ISO, and no
network, so the command correctly exits 2 at the prerequisite check instead
of claiming a boot result. The script is ready for a host with those
prerequisites; it verifies the ISO's SHA-256
(`9afc98ed2bb15a3ff26ebaca12ea392079292df6667b3c1c527fdd30d80cdb13`)
before booting and uses QEMU TCG with `-display none -nic none
-machine pc,kernel-irqchip=off` and no writable disk.

| Case | Expected | Result here |
| --- | --- | --- |
| Official v0.1.2 ISO digest | matches the published SHA-256 | BLOCKED (ISO absent) |
| Boot + `HBEACON TempleOfHermes/` | beacon on COM1 | BLOCKED |
| Create `B:/Home/hermes/Src/` | `HOME DIRS OK` | BLOCKED |
| Push `Home.HC` and `HomeTest.HC` to B: | both pushes `ok:1` | BLOCKED |
| Compile `Home.HC` over `eval` | `HOME HC OK`, no compile error | BLOCKED |
| Run `HomeTest.HC` | `HOME TEST DONE`, result file `PASS` | BLOCKED |
| `JOURNAL.TXT` | 3 lines, timestamped, no tabs/controls, line 3 exactly 200 chars | BLOCKED |
| `PROJECTS.TXT` | exactly `Current: Temple of Hermes` + `Next: Write HOME-DIR docs` | BLOCKED |
| `JournalTail(3)` | returns `session one` and `sessiontwonext` | BLOCKED |
| No C: | `HomeInit(NULL,'C')` returns `ERR ...`, no debugger text | BLOCKED |
| Screendumps | 2 PIL-checked 640x480 PNGs | BLOCKED (Pillow absent) |

When run on a host with the prerequisites, the script writes
`home-journal.json`, `home-journal-com1.log`, the two screenshots, and the
pulled `JOURNAL.TXT` / `PROJECTS.TXT` / result bodies into this directory
(plus raw captures under the ignored `shots/_raw/` tree).

## Shots

0 of the allowed 3 shots were produced because this sandbox has no QEMU or
Pillow. The script takes two screendumps and checks each with Pillow
(`640x480`, colour count) before saving; it does not use any non-PIL image
tool.

## Open items for the coordinator

- Run `python3 scripts/test_home_journal.py` on a host with QEMU, Pillow, and
  `dist/TempleOfHermes-0.1.2.ISO` to fill the QEMU matrix above. No source
  change is needed.
- The preinstalled disk image work (TOH-DISK-IMAGE) is expected to provide a
  persistent C:. Until that image boots, live-CD sessions should use B: and
  treat the journal as ephemeral.
