# Hermes lore QEMU shots

Proof that the CODEX OF NOUS renders under QEMU TCG on the public TinkerOS
5.20-rc10 live CD. Nothing is installed; `Once.HC` is not touched.

## Reproduce

```bash
sudo apt-get update
sudo apt-get install -y qemu-system-x86 qemu-utils

curl -L -o /tmp/TinkerOS_5.20-rc10.ISO \
  https://github.com/tinkeros/TinkerOS/releases/download/5.20-rc10/TinkerOS_5.20-rc10.ISO
sha256sum /tmp/TinkerOS_5.20-rc10.ISO
# feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4

TOH_TINKEROS_ISO=/tmp/TinkerOS_5.20-rc10.ISO \
  python3 shots/hermes-lore/run_qemu.py
```

The harness uses `-accel tcg -display none -nic none -machine
pc,kernel-irqchip=off`. It pushes `demo/DEMO1..3.HC` over COM1 into the live
CD's writable `B:` RAM drive and includes them.

## Why a demo source

The canonical lore lives in `Hermes/Lore/` (see `docs/LORE.md`). The live CD's
compiler heap is small, so the harness uses compact renderings of the same
entries, keeping each include under about 1.6 KB. Sourced lines keep their
public URLs; original lines stay marked as new.

## Shots

| File | Content |
|---|---|
| `00-boot.png` | live CD first boot |
| `01-after-install-prompt.png` | installer answered NO |
| `02-live-cd.png` | live CD shell |
| `03-codex-index.png` | Codex index |
| `04-codex-hermes.png` | Hermes entry + Wikipedia URL |
| `05-codex-nous.png` | Nous Research entry + site URL |
| `06-motd.png` | message of the day |
| `07-oracle.png` | oracle verse |
| `08-capybara.png` | capybara art + sourced fact |
| `09-caduceus.png` | caduceus art + source URL |
| `10-aletheia.png` | hidden latch |

`serial-transcript.txt` records the pushed sizes and the R/D/W acks.
