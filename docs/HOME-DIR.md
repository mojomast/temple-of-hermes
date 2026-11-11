# Hermes home directory

Slice B of the community plan gives a Hermes agent a small, predictable
home on the guest filesystem: a daily journal, a current project with a next
step, and a `Src/` folder for small HolyC programs. The helpers live in
`Adam/Hermes/Home.HC` and are pulled in by the single
`#include "Home"` line in `Adam/Hermes/Load.HC`.

## Layout contract

The host plugin's `session_start` reader on `hermes-templeos`
(`feat/community-ops`) reads exactly these paths:

```text
C:/Home/<handle>/
  JOURNAL.TXT      one line per session, newest appended at the end
  PROJECTS.TXT     "Current: <project>" and "Next: <next step>"
  Src/             small programs (HolyC and anything printable)
```

- `<handle>` is 1-32 characters of `A-Z`, `a-z`, `0-9`, `.`, `-`, `_`.
  The default is `hermes`. An invalid handle is rejected with
  `ERR bad_handle`; no directory is created.
- `JOURNAL.TXT` is plain text. Each line is `YYYY-MM-DD HH:MM <text>`,
  at most 200 characters, with no tabs or control characters. Lines are
  appended, so the newest session is last.
- `PROJECTS.TXT` is plain text. This implementation writes exactly:

  ```text
  Current: <project>
  Next: <next step>
  ```

  The host reader also accepts `Project:` and `Todo:`, but the helpers
  always write `Current:` and `Next:`.
- Paths are case-sensitive in practice. Write the names exactly as shown.

## Helper reference

All helpers return a freshly allocated string. A successful call returns
`OK ...`; a failure returns `ERR <code>` and never enters the debugger.
The caller owns the string and frees it. Include `Home.HC` through
`Adam/Hermes/Load.HC`, or compile it after that file in a guest session.

| Helper | Behaviour |
| --- | --- |
| `HomeInit(U8 *handle=NULL, U8 drv='C')` | Validate the handle, select the drive, and create `<drv>:/Home/<handle>/Src/`. Returns `OK <dir>` or `ERR bad_handle`, `ERR bad_drive`, `ERR drive_not_writable:<d>`, `ERR mkdir_failed`. |
| `HomeDir()` | Return the selected home path, or `ERR not_initialized`. |
| `JournalAdd(U8 *text)` | Append one timestamped line. CR, LF, tab, DEL, and other control bytes are removed; the whole line is capped at 200 chars. Returns `OK journal_added` or `ERR not_initialized`/`ERR write_failed`. |
| `JournalTail(I64 n=5)` | Return the last `n` lines (1-100, newest last), or `ERR no_journal`. |
| `ProjectSet(U8 *current, U8 *next)` | Overwrite `PROJECTS.TXT` with the `Current:` and `Next:` lines. Controls are stripped and each value is capped at 200 chars. |
| `ProjectShow()` | Return `PROJECTS.TXT`, or `ERR no_projects`. |

Typical use in a guest session:

```holyc
#include "C:/Adam/Hermes/Load.HC";
r=HomeInit("hermes",'C');
Free(r);
r=JournalAdd("Synced the day's notes and checked the next step.");
Free(r);
r=ProjectSet("Temple of Hermes","Finish the home-directory docs");
Free(r);
JournalTail(5);
```

`JournalTail` and `ProjectShow` return an allocated string; print it or
free it when done.

## Drives and persistence

- **C: persists** when the guest boots the preinstalled disk image that is
  being produced in TOH-DISK-IMAGE. Use `HomeInit(handle,'C')` there; the
  journal and project file survive reboots.
- **B: is RAM only.** The live CD creates B: from the initramfs. It is
  writable immediately but disappears on power-off. Use it for tests and
  for a live-CD session where nothing can be saved. Document the loss to
  the user; do not imply it is durable.
- **The boot CD is read-only.** The ISO drive (T: on the live CD) must
  never be a write target. `HomeInit` checks `DrvIsWritable` and returns
  `ERR drive_not_writable:<d>` instead of attempting a write.
- If C: is absent (the usual live-CD case), `HomeInit(NULL,'C')` returns
  `ERR drive_not_writable:C` as a normal string. Call
  `HomeInit(NULL,'B')` for an ephemeral live session. No helper formats,
  installs, or asks a yes/no question.

## How the host reads it

The host plugin's `session_start` reader pulls the three paths above over
HRPC (the daemon `pull` op). It:

1. reads `JOURNAL.TXT`, splits it into lines, and keeps the last
   timestamped entries (each line must match
   `^\d{4}-\d{2}-\d{2} \d{2}:\d{2} ` and be at most 200 chars);
2. reads `PROJECTS.TXT` and takes the values after `Current:` (or
   `Project:`) and `Next:` (or `Todo:`);
3. lists `Src/` for small programs the agent can inspect or run.

The helpers only guarantee the file formats above. They do not read the
host, open a network connection, or start a service.

## Tests

- Guest regression: `Adam/Hermes/HomeTest.HC` runs init, three
  `JournalAdd` calls (including a tab/newline case and a 300-char case),
  `JournalTail`, `ProjectSet`, `ProjectShow`, a bad-handle case, and the
  no-C: error path against B:, then writes
  `B:/Home/hermes/HOME-TEST.TXT`.
- Host test: `scripts/test_home_journal.py` boots the official v0.1.2 ISO
  live (sha256 verified), creates the B: directories, pushes `Home.HC` and
  `HomeTest.HC`, runs them over HRPC `eval`, pulls `HOME-TEST.TXT`,
  `JOURNAL.TXT`, and `PROJECTS.TXT`, and asserts the contract above.
  `--static` runs the source/contract checks without QEMU.
- Evidence and the result matrix are in `shots/hermes-home-0.1.3/`.
