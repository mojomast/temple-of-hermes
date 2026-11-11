# Hermes Apps QEMU evidence

Booted the public TinkerOS 5.20-rc10 ISO under QEMU TCG:

```
-accel tcg -display none -nic none -machine pc,kernel-irqchip=off
```

The `Hermes` tree and `Once.HC` / `PersonalMenu.DD` were placed on a
writable FAT32 IDE disk, mounted as `C:`, then `Once.HC` was executed.
Screenshots are QMP `screendump` PNGs.

| Shot | What it shows |
| --- | --- |
| `01-once-launcher.png` | `Once.HC` welcome text and the autostarted launcher; footer reads `Art icons: 9/9`. |
| `02-selected-chat.png` | `Hermes Chat` selected; status says it is planned, not implemented. |
| `03-welcome.png` | The preserved `Once.HC` welcome text on its own. |
| `04-personal-menu.png` | Bottom of `PersonalMenu.DD` with the `Temple of Hermes` section and its 16x16 packed sprites. |

The `.txt` files beside each PNG are the bitmap-font OCR of that screen,
kept as a text search index for the evidence.
