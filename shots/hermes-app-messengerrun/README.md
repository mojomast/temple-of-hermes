# Messenger Run QEMU evidence

Captured from the public TinkerOS 5.20-rc10 live CD in QEMU with TCG only:

```
-accel tcg -display none -nic none -machine pc,kernel-irqchip=off
```

The ISO SHA-256 used for these captures is
`feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4`.

The game was loaded from a FAT32 data disk at
`C:/Hermes/Apps/MessengerRun`, not from the CD. Shots are QMP `screendump`
PNGs at 640x480.

| Shot | What it shows |
| --- | --- |
| `01-human-arcade.png` | Fresh human run; title, board, HUD, and controls |
| `02-human-run.png` | Human run after the lane has started moving |
| `03-agent-play-on.png` | `A` pressed; `AGENT PLAY`, `AUTOPILOT ON`, and the live auto-action line |
| `04-agent-play-action.png` | Autopilot collecting scrolls and climbing the score |
| `05-agent-play-later.png` | Longer agent run with continued score gain |
| `06-human-resumed.png` | `A` pressed again; control returned to the human |
| `07-paused.png` | `P` pause overlay |
| `08-return-to-shell.png` | `Esc` exits cleanly back to the C: prompt |
| `09-agentplay-include.png` | `#include ".../AgentPlay"` starts agent-play directly |
| `10-agentplay-include-run.png` | Direct agent-play entry point after several seconds |
