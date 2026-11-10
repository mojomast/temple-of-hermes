# Hermes tools — QEMU TCG evidence

Captured from the sandbox with QEMU `-accel tcg -display none -nic none
-machine pc,kernel-irqchip=off`, no KVM, no networking.

| File | What it shows |
| --- | --- |
| `01-live-prompt.png` | Stock TinkerOS 5.20-rc10 live desktop with the command prompt focused. |
| `02-live-comm.png` | `CommInit8n1(1,115200)` plus the `COMMOK` marker on COM1. |
| `03-receiver-compiled.png` | The serial receiver definition accepted and `DEFOK` printed. |
| `04-receiver-started.png` | `R;` entered; the receiver creates `T:/Adam/Hermes` and begins reading a pushed file. |
| `test-results.txt` | `python3 -m pytest -q host/tests/test_hermes_daemon_client.py` (12 passed). |
| `*.txt` | Tesseract transcription of each screendump. |

The full image build was also driven under TCG, but this sandbox's guest-side
legacy `RedSeaISO` path could not complete the expanded staged tree on the
live RAM drive. A booted-image screenshot of `toast`, `windows`, `guards`, and
`sysinfo` is therefore not present here; those RPCs are covered by the host
client suite and the contract in `docs/HERMES-TOOLS.md`.
