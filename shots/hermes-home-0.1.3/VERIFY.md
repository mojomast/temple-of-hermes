# Hermes home directory (slice B) verification

- Packed workspace base: `0d6bc0100a4211a9aee09833b9493723423d9959`
  (WIP on daemon-fix `2071daa`, local squash commit `f035a4f`).
- Work branch: `hermes/home-journal`; every change is uncommitted in the
  worktree.
- Assigned changes: `Adam/Hermes/Home.HC`, `Adam/Hermes/HomeTest.HC`, the
  existing one `#include "Home"` line in `Adam/Hermes/Load.HC`,
  `scripts/test_home_journal.py`, `docs/HOME-DIR.md`, and this evidence
  directory.

## Layout under test

```text
C:/Home/<handle>/
  JOURNAL.TXT      "YYYY-MM-DD HH:MM <text>", one per session, <=200 chars
  PROJECTS.TXT     "Current: <project>" and "Next: <next step>"
  Src/             small programs
```

`<handle>` is 1-32 of `A-Z a-z 0-9 . - _`; the default is `hermes`.
`HomeInit` creates the directories, `JournalAdd` appends and sanitises,
`JournalTail` reads the newest lines, and `ProjectSet`/`ProjectShow` write
and read the two project lines. Every helper returns an allocated
`OK ...` or `ERR <code>` string. `HomeInit` checks `DrvIsWritable`, so a
missing or read-only drive is an error string, never a debugger.

## Environment and guest image

- `qemu-system-x86_64` `1:8.2.2+ds-0ubuntu1.18` and `qemu-img` installed
  from the Ubuntu archive; Pillow installed (`python3-pil`).
- ISO downloaded with `curl -L` from the published v0.1.2 release URL and
  verified before use:
  `9afc98ed2bb15a3ff26ebaca12ea392079292df6667b3c1c527fdd30d80cdb13`.
- QEMU TCG, no KVM: `-machine pc,kernel-irqchip=off -accel tcg
  -display none -nic none -m 2G`, ISO as CD, no writable disk.
- The official ISO answers `HBEACON TempleOfHermes/0.1.0`; its daemon
  predates the 0.1.3 file-op work. Two test accommodations, both visible in
  `scripts/test_home_journal.py`:
  - its request buffer is about 2 KB (a 2525-byte push killed the daemon
    task), so sources are pushed in 1800-byte pieces and merged in the
    guest by `FileRead`/`FileWrite`;
  - its `eval` does not capture the guest output document, so every
    assertion reads a file the guest wrote and pulls it over HRPC instead
    of trusting `eval` text.

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

Logs: `home-journal-static.log`, `home-journal-static.json`.

## QEMU matrix (executed)

Command: `python3 scripts/test_home_journal.py`

Result: **24/24 PASS** (exit 0). `home-journal.json` records every check.

The test leaves `B:/Home/hermes/` absent after creating only `B:/Home`, so
the journal/project paths and `Src/` in the matrix are created by
`HomeInit` itself.

| # | Check | Expected | Result |
| --- | --- | --- | --- |
| 1 | `beacon` | `HBEACON TempleOfHermes/` on COM1 | PASS `HBEACON TempleOfHermes/0.1.0` |
| 2 | `b_root` | push into `B:/Home` succeeds | PASS `{"wrote":155}` |
| 3 | `b_root_pull` | marker round-trips | PASS `ok` |
| 4 | `push_home` | chunked push + merge of `Home.HC` | PASS |
| 5 | `push_home_test` | chunked push + merge of `HomeTest.HC` | PASS |
| 6 | `pull_source_home` | 4077 bytes back, identical | PASS |
| 7 | `pull_source_home_test` | 3551 bytes back, identical | PASS |
| 8 | `compile_home` | `HomeDir()` links before init | PASS `ERR not_initialized` |
| 9 | `run_reply` | `#include "B:/Home/HomeTest.HC"` accepted | PASS |
| 10 | `pull_result` | `HOME-TEST.TXT` pulled | PASS |
| 11 | `pull_journal` | `JOURNAL.TXT` pulled | PASS |
| 12 | `pull_projects` | `PROJECTS.TXT` pulled | PASS |
| 13 | `result_pass` | guest result is `HERMES HOME TEST PASS`, no `FAIL` | PASS (9/9 sub-checks) |
| 14 | `home_src_created` | push into `B:/Home/hermes/Src` succeeds | PASS `{"wrote":195}` |
| 15 | `home_src_pull` | marker round-trips | PASS `ok` |
| 16 | `journal_format` | 3 lines, `YYYY-MM-DD HH:MM `, no tabs/controls, <=200 | PASS |
| 17 | `journal_session_one` | first line ends `session one` | PASS |
| 18 | `journal_control_stripped` | tab/newline input becomes `sessiontwonext` | PASS |
| 19 | `journal_truncated_200` | 300-char input becomes a 200-char line | PASS `len=200` |
| 20 | `projects_format` | exactly `Current:` + `Next:` | PASS |
| 21 | `projects_values` | `Current: Temple of Hermes` / `Next: Write HOME-DIR docs` | PASS |
| 22 | `journal_tail` | `JournalTail(3)` returns both session lines | PASS |
| 23 | `no_c_error` | `HomeInit(NULL,'C')` returns an error string, no debugger | PASS `ERR drive_not_writable:C` |
| 24 | `daemon_alive` | `ping` still answers after the no-C call | PASS `{"pong":1,...}` |

Pulled journal (line lengths 31, 35, 200):

```text
2026-11-11 22:38 session one
2026-11-11 22:38 sessiontwonext
2026-11-11 22:38 XXXXX… (183 X characters)
```

Pulled projects file:

```text
Current: Temple of Hermes
Next: Write HOME-DIR docs
```

`B:/Home/hermes/HOME-TEST.TXT` contained `HERMES HOME TEST PASS` with
`b_init`, `journal_add_1`, `journal_add_2`, `journal_add_long`,
`journal_tail`, `project_set`, `project_show`, `bad_handle`, and
`no_c_error` all `PASS`.

C: was absent on the live CD (`DrvIsWritable('C')` returned NULL), so the
guest took the no-C error path; the script would validate `C:/Home/hermes/`
instead when C: is writable.

Logs: `home-journal.log` (matrix transcript), `home-journal-com1.log`
(COM1 transcript), `home-journal.json` (machine-readable result).

## Shots

Two of the allowed three, both captured with QMP `screendump` and validated
with Pillow only (`640x480`, colour count). No PNG was opened or viewed
in-model.

| Shot | Size | Colours | Check |
| --- | --- | --- | --- |
| `01-home-journal-boot.png` | 640x480 | 5 | PASS |
| `02-home-journal-run.png` | 640x480 | 15 | PASS |

## Persistence notes

- B: is RAM only. Everything in this matrix disappears on power-off; the
  test never implies otherwise.
- C: is the persistent target when the TOH-DISK-IMAGE preinstalled disk
  image provides it. This matrix could not exercise C: because the live CD
  has no writable C:.
- The boot CD was never a write target; `HomeInit` rejects a non-writable
  drive before any `DirMk`/`FileWrite`.

## Open items for the coordinator

- The published v0.1.2 ISO carries the older 0.1.0 daemon. Running this
  matrix against a CD built from the packed 0.1.3 tree would additionally
  exercise single-shot pushes and eval-output capture; no source change is
  needed for that.
- C: persistence remains owned by TOH-DISK-IMAGE; this slice only defines
  and tests the layout and helpers.
