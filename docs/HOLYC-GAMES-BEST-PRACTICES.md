# HolyC Games Best Practices (TempleOS / TinkerOS / Temple of Hermes)

This guide is for small games under `Hermes/Apps/<Game>/`. It extends
`docs/HOLYC-BEST-PRACTICES.md` (HolyC app conventions on `hermes/holyc-guide`,
commit `482269b`; that file is **not** present on `hermes/art-nous` at
`fdb2f54`). Nothing here requires a host-side HolyC compiler: the guest OS
compiles the sources. The sandbox target is TinkerOS 5.20-rc10 under QEMU TCG.

## Sources (in-tree, version-matched to this tree unless noted)

- `Demo/Templates/Game1.HC` — the canonical game skeleton (`SettingsPush`,
  `Spawn` song/animate tasks, `Fs->draw_it`, `GetKey` loop, `Init`/`CleanUp`).
- `Demo/Games/` — working games to copy structure from, especially
  `FlapBat.HC`, `BattleLines.HC`, `CastleFrankenstein.HC`, `Talons.HC`,
  `TheDead.HC`, `Whap.HC`, `RainDrops.HC`, `Squirt.HC`, `Digits.HC`.
- `Doc/GraphicsOverview.DD` — CDC / `draw_it` / sprites / `GrBlot`.
- `Doc/TextBase.DD`, `Adam/Gr/GrTextBase.HC` — `gr.text_base` updates in
  `draw_it`.
- `Doc/CharOverview.DD`, `Demo/MsgLoop.HC` — keys, scan codes, messages.
- `Adam/WinMgr.HC` (`Refresh`), `Kernel/KGlbls.HC` (`fps_master=30`).
- `Kernel/KCfg.HH` — `GR_WIDTH 640`, `GR_HEIGHT 480`.
- `Adam/Gr/GrPalette.HC`, `Kernel/KernelA.HH` (`COLORS_NUM 16`).
- `Adam/Gr/GrDC.HC` — `DCNew` / `DCAlias` / `DCDel`.
- `Apps/Chess/Load.HC`, `Apps/Chess/Run.HC`, `Hermes/Apps/Template/`.
- `Hermes/Apps/MessengerRun/` on `hermes/app-messengerrun` — an existing
  Temple of Hermes game with an agent-play flag (pattern only; do not edit it
  from a game-feature branch).

Public project docs (linked, not quoted at length):

- TinkerOS: <https://github.com/tinkeros/TinkerOS>
- TinkerOS 5.20-rc10: <https://github.com/tinkeros/TinkerOS/releases/tag/5.20-rc10>
- Docs portal: <https://tinkeros.github.io/>
- TempleOS: <https://templeos.org/>

## 1. Start from Game1, not a blank main loop

`Demo/Templates/Game1.HC` is the pattern almost every `Demo/Games/` title
follows:

1. `SettingsPush;` (see `SettingsPush`) so palette, window, and song state
   can be restored with `SettingsPop`.
2. Optional `Fs->song_task=Spawn(&SongTask,NULL,"Song",,Fs);` with
   `Fs->task_end_cb=&SndTaskEndCB;` inside the song task, and
   `MusicSettingsRst;` / `Play(...)` in a loop.
3. `AutoComplete; WinBorder; WinMax; DocCursor; DocClear; MenuPush(...);`
4. `Init;` then `Fs->animate_task=Spawn(&AnimateTask,NULL,"Animate",,Fs);`
   and `Fs->draw_it=&DrawIt;`.
5. A `try { while (TRUE) switch (GetKey(&sc)) { ... } } catch PutExcept;`
   input loop. Restart with `CleanUp; Init;` on `'\n'`; exit on
   `CH_ESC` / `CH_SHIFT_ESC` via a label **inside** the try
   (`mg_done:` in Game1 — "Don't goto out of try").
6. `SettingsPop; CleanUp; MenuPop;`.

Draw in `DrawIt(CTask *task, CDC *dc)`. Advance physics/AI in `AnimateTask`
or in the input loop with `Sleep`/`Refresh`. Do not busy-spin.

## 2. `Fs->draw_it` is called by the WinMgr, typically 30 fps

This is **30 fps**, not 60. Sources:

- `Adam/WinMgr.HC` — `Refresh` is documented "Wait for 30fps WinMgr to start
  & finish scrn refresh."
- `Kernel/KGlbls.HC` — `I64 fps_master=30;` (TinkerOS can change
  `fps_master` in `Adam/Gr/GrScrn.HC`, but the default is 30).
- `Doc/GraphicsOverview.DD` — "You change the `Fs->draw_it` var to point to
  your `DrawIt()` function which gets called each scrn refresh (30 fps).
  You draw everything in the window over and over again."
- `Doc/TextBase.DD` / `Adam/Gr/GrTextBase.HC` — `gr.text_base` "must be
  updated 30fps in your `Fs->draw_it()` callback."
- `Demo/Graphics/SunMoon.HC` — `Refresh; //Typically 30 fps`.
- `Demo/Games/TheDead.HC` — "Called by the Window Mgr system task 30fps."

Only tasks on Core0 may have windows; one window per task. Pop-ups are child
**tasks**, not child windows (`Doc/GraphicsOverview.DD`).

`DrawIt` should be fast: plot with `GrPlot` / `GrLine` / `GrRect` / `GrCircle`
/ `GrPrint` / `Sprite3` on the `CDC *dc` the WinMgr passed in. Prefer not to
allocate, compile, or block inside `draw_it`. `Refresh` waits for one (or
`cnt`) WinMgr frames and can pump messages (`Adam/WinMgr.HC`). Long loops
must `Yield` or `Sleep` so the WinMgr can run.

## 3. Device contexts (`CDC`) and the drawing model

From `Doc/GraphicsOverview.DD` and `Adam/Gr/GrDC.HC`:

- A `CDC` holds color, thick, a optional bitmap, and a transform matrix.
  The WinMgr passes one into `DrawIt`. `dc->color` is a `CColorROPU32`
  (raster-op in bits 8-11; see `ROP_EQU`, `ROP_COLLISION`).
- `DCAlias(dc=NULL, task=NULL)` copies a DC so you can change pen/color
  without clobbering the original. `NULL` means `gr.dc`. Always `DCDel`
  the alias when finished. Signature check is `DCS_SIGNATURE_VAL`.
- `gr.dc` is the persistent screen layer (does not need to be redrawn every
  frame). Most games should **not** scribble on `gr.dc`; redraw in `draw_it`.
- `DCNew(width, height, task=NULL)` allocates an off-screen bitmap. Width is
  rounded up to a multiple of 8 (`width_internal=(width+7)&~7`). `GrBlot`
  it onto the window DC. `DCDel` frees body, matrix, and depth buffer
  (aliases must not free the borrowed body).
- `RainDrops.HC` keeps a `cur_dc` and `GrBlot`s into it to collide drops
  against geometry — a good off-screen pattern.
- A full 640x480 bitmap is large (~307 KB). Live-CD compiler/heap limits
  mean **at most one 640x480 `.GR` resident** at a time. Prefer 16/32/64
  icons, header plates (e.g. 640x160), or `Sprite3` of compact `$SP$`
  sprites over loading every wallpaper.

## 4. Sprites and `.GR` assets

- Press `<CTRL-r>` in the editor to create an embedded sprite; `<CTRL-t>`
  shows the `$SP,"<n>",BI=n$` placeholder. Plot with
  `Sprite3(dc,x,y,0,$IB,"<n>",BI=n$);` (`Doc/GraphicsOverview.DD`,
  `Demo/Graphics/SpritePlot.HC`, and almost every `Demo/Games/` title).
- External `.GR` files (Temple of Hermes art lives under `Hermes/Art/`) are
  loaded with the existing GR helpers in-tree. Use official
  `hermes/art-nous` assets; do not invent stand-in faces or plates.
- Palette must be the standard 16-color TempleOS palette
  (`Adam/Gr/GrPalette.HC` `gr32_palette_std`, also listed in `docs/ART.md`):

  | # | Name | RGB |
  |---|------|-----|
  | 0 | BLACK | `#000000` |
  | 1 | BLUE | `#0000AA` |
  | 2 | GREEN | `#00AA00` |
  | 3 | CYAN | `#00AAAA` |
  | 4 | RED | `#AA0000` |
  | 5 | PURPLE | `#AA00AA` |
  | 6 | BROWN | `#AA5500` |
  | 7 | LTGRAY | `#AAAAAA` |
  | 8 | DKGRAY | `#555555` |
  | 9 | LTBLUE | `#5555FF` |
  | 10 | LTGREEN | `#55FF55` |
  | 11 | LTCYAN | `#55FFFF` |
  | 12 | LTRED | `#FF5555` |
  | 13 | LTPURPLE | `#FF55FF` |
  | 14 | YELLOW | `#FFFF55` |
  | 15 | WHITE | `#FFFFFF` |

  `COLORS_NUM` is 16 (`Kernel/KernelA.HH`). Do not invent 24-bit colors.
  Screen shots used for acceptance are checked with PIL: unique indices
  must be 0-15, and the image should be 640x480.

## 5. Input: `GetKey`, `ScanChar`, messages, and the mouse

From `Doc/CharOverview.DD` and `Demo/Games/`:

- A key is a scan code: low `U8` is the key, upper bytes are flags
  (`SCF_CTRL`, `SCf_KEY_UP`, …). `GetKey(&sc)` in Game1 blocks until a
  key; `sc.u8[0]` is `SC_CURSOR_LEFT` / `RIGHT` / `UP` / `DOWN`. ASCII
  comes back as the function result (`'\n'`, `CH_ESC`, `CH_SHIFT_ESC`).
- `ScanChar` / `ScanKey` are the non-blocking relatives (used by
  `BattleLines.HC`). `Bt(kbd.down_bitmap, sc)` tests a key that is
  currently held (`RainDrops.HC`).
- For held/repeat action (shoot, flap), prefer the message loop in
  `TheDead.HC`: `ScanMsg(&arg1,&arg2,1<<MSG_KEY_DOWN | 1<<MSG_KEY_UP)`.
  On keyboard msgs, `arg1` is the ASCII char and `arg2` is the scan code.
  See also `Demo/MsgLoop.HC` and `Doc/CharOverview.DD`.
- Mouse: `ms.pos.x` / `ms.pos.y` are screen coordinates. Convert to
  window space with `ms.pos.x-task->pix_left-task->scroll_x` (and the
  matching `pix_top` / `scroll_y`), as in `Whap.HC` and `Adam/WinMgr.HC`
  `WinQueIPMsgs`.
- Drive guest typing slowly from the host; the TinkerOS keyboard FIFO
  drops characters if a long `#include` line is dumped at once.

## 6. Sound and music

- Short effects: `Snd(freq);` / `Snd;` to stop (`Whap.HC`), or `Beep`
  (`Digits.HC`).
- Background song: a child task as in Game1 (`SongTask` + `Play("4AB5C");`
  in a loop). Set `Fs->task_end_cb=&SndTaskEndCB;` so the speaker is
  silenced when the task dies. Call `MusicSettingsRst;` at the start of
  the song task.
- Keep song and animate tasks parented to the game task (the `Spawn(...,,Fs)`
  form in Game1) so they are cleaned up on exit.

## 7. Pacing, tasks, and memory

- `Sleep(10);` yields for ~10 ms (`TheDead.HC`). `Refresh;` syncs to the
  next WinMgr frame. `Yield;` if you only need to let other tasks run.
- `Spawn(&Fn,data,"Name",,Fs)` creates a `CTask`. `Kill` leftover tasks
  on exit if they are not already parented. Use `try`/`catch`/`PutExcept`
  so a panic still `SettingsPop`s.
- HolyC stacks do not grow: allocate with `MAlloc` / `CAlloc` / `DCNew`
  and `Free` / `DCDel`. Do not recurse deeply or put large arrays on the
  stack.
- Split sources (`Load.HC` includes compact `.HC` files). A single huge
  include can exhaust the live-CD compiler heap; keep include chunks
  small (a previous Codex.HC failed for this reason; compact includes
  around ~1.6 KB compiled cleanly).

## 8. Globals, scores, and collisions

- Demo games often use file-scope globals (`FlapBat.HC`, `TheDead.HC`).
  That is fine in a self-contained app directory if names are unique.
  Prefix globals (`cad_`, `tr_`, `dd_`, `sp_`) or wrap state in a class
  (see `Trooper` in `BattleLines.HC`) so two games loaded in one session
  do not collide.
- Stock demos persist best scores with `RegDft("TempleOS/GameName",...)`
  and `RegExe` (`FlapBat.HC`, `CastleFrankenstein.HC`). **Temple of Hermes
  games should instead write a high-score / result file under `C:/Tmp`**
  (the live CD and guest tests may not want Registry mutations, and
  `C:/Tmp` is writable). Use `FileWrite` / `FileRead` or `DocWrite`.
- Do not edit `Once.HC`, `Adam/Hermes/`, `MakeDistro.HC`, or
  `Hermes/Apps/Registry.HC` from a game branch.

## 9. `Load.HC` / `Run.HC` and `Cd(__DIR__);;`

Same split as `docs/HOLYC-BEST-PRACTICES.md` and `Apps/Chess/`:

```holyc
// Load.HC
#help_index "Games"
Cd(__DIR__);;
#include "MyGame"
#help_index ""
```

```holyc
// Run.HC
Cd(__DIR__);;
#include "Load"
MyGame;
```

- `Cd(__DIR__);;` must be the first statement (a `#help_index` line may
  precede it). It makes includes and data files relative to the app dir.
- **Do not use `__DIR__` in global initializers** — that broke a previous
  guest compile. Use relative paths after `Cd(__DIR__);;`.
- `Load.HC` must have no windows, prompts, or game start. It must be safe
  to include more than once.
- `Run.HC` is the only file with top-level side effects.
- Running `Run.HC` a second time must work (reset state in `Init` /
  `CleanUp`; return to a usable shell).

## 10. Agent-drivable mode

Hermes agents need to play and test the game without OCR. Follow the
spirit of `Hermes/Apps/MessengerRun` (`MessengerRun(TRUE)` / `AgentPlay.HC`
on `hermes/app-messengerrun`):

- Expose a HolyC entry such as `MyGameAgent(U8 *out_file)` or
  `MyGame(Bool agent=FALSE)` that runs a deterministic or scripted
  session (fixed seed, canned inputs, or a short AI policy).
- Write a plain-text result file under `C:/Tmp` (score, result=`PASS`/`FAIL`
  or a numeric score, maybe frame count). Also persist a high-score file
  under `C:/Tmp`.
- Interactive play still uses the Game1 key loop. Agent mode must finish
  on its own (bounded length) so a QEMU guest script can `#include` it
  and then `Type("C:/Tmp/MyGameResult.TXT");`.

## 11. Checklist

- [ ] `Load.HC` / `Run.HC` split; `Cd(__DIR__);;` first; no side effects in Load.
- [ ] Compiles and runs twice on TinkerOS 5.20-rc10 (QEMU TCG); returns to a shell.
- [ ] `Fs->draw_it` + `Sleep`/`Refresh`/`Yield`; no busy loop.
- [ ] 16-color standard palette only; at most one 640x480 `.GR` resident.
- [ ] Official `hermes/art-nous` art; no stand-in faces; no photoreal likeness.
- [ ] High score + agent result under `C:/Tmp`; agent mode needs no bitmap OCR.
- [ ] Unique global prefixes; `SettingsPush`/`Pop`; spawned tasks cleaned up.
- [ ] New flavor lines marked `NEW`. No fabricated real-person quotes.
- [ ] Announcer name is Southpaw only — never print `TurboFit` / `TURBOFIT`.
- [ ] Feature branch only; secret-scan before push; no merge, tag, or force-push.
