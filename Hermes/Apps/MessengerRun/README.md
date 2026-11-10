# Messenger Run

`Hermes/Apps/MessengerRun` is a TempleOS/TinkerOS arcade game for THE TEMPLE OF
HERMES. Hermes runs the temple courier lane: collect falling message scrolls,
grab caduceus seals for an extra life, and dodge storm cells. The longer the run,
the faster the lane moves.

The app icon is generated from the Art branch asset
`Hermes/Art/Icons/32/messenger-run.SP` and is stored here as `Icon.HC`.

## Run

From a HolyC prompt, in the guest:

```holyc
#include "::/Hermes/Apps/MessengerRun/Run"
```

`Run.HC` changes into the app directory, loads `MessengerRun.HC`, and starts a
human game. When installed under `C:/Apps/MessengerRun`, use
`#include "C:/Apps/MessengerRun/Run";` instead.

## Controls

| Key | Action |
| --- | --- |
| Left / Right arrows | Move Hermes one lane |
| `A` | Toggle agent-play autopilot |
| `P` | Pause / resume |
| Enter | Restart after a run ends |
| Esc / Shift-Esc / Ctrl-Q | Quit |

## Agent-play mode

Messenger Run ships with a documented, in-game **agent-play** mode. Press `A`
at any time, or launch it directly:

```holyc
#include "::/Hermes/Apps/MessengerRun/AgentPlay"
```

`AgentPlay.HC` calls `MessengerRun(TRUE)`; the same entry point is available from
a loaded session as `MessengerRun(TRUE);`.

In agent-play the autopilot reads the live lane state every frame and chooses a
lane using the same moves a human has:

- `AUTO: DODGE STORM` - the current or target lane is unsafe, so it moves to a
  clear adjacent lane.
- `AUTO: SAFE ROUTE` - the nearest scroll is guarded; it holds a safe lane.
- `AUTO: SEEK SCROLL` - it closes on the lowest uncollected scroll.
- `AUTO: PATROL LANE` - no scroll is on the board, so it returns to centre.

The HUD displays `AGENT PLAY` and `AUTOPILOT ON` while the mode is active. Press
`A` again to return to human control without ending the run. The autopilot is
deterministic and only sees on-screen game state, so an external agent can use
the same keyboard interface or compare against the same behaviour.

## Scoring

- Deliver a scroll: 10 points times the combo multiplier. Every five deliveries
  raises the multiplier, up to x6.
- Collect a caduceus seal: 25 points and one extra life, up to five lives.
- Storm hit: lose a life and 20 points; a missed scroll resets the combo.
- A run ends at zero lives. `BEST` is saved with the Temple registry key
  `TempleOfHermes/MessengerRun` (the old `TinkerOS/MessengerRun` key is
  migrated on first run).

## Files

| File | Purpose |
| --- | --- |
| `Run.HC` | Normal human-play entry point |
| `AgentPlay.HC` | Agent-play entry point |
| `Load.HC` | Library load plus `Games` help index |
| `MessengerRun.HC` | Game, renderer, input, and autopilot |
| `Icon.HC` | 32x32 Art messenger-run icon |
| `README.md` | This document |

## Verification

The companion evidence lives in `shots/hermes-app-messengerrun/` and was captured
from TinkerOS 5.20-rc10 under QEMU with `-accel tcg -display none -nic none`.
