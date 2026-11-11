Threshold QEMU TCG evidence
===========================

Guest: TinkerOS 5.20-rc10 live ISO
SHA256: feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4
Accel: -accel tcg -display none -nic none -machine pc,kernel-irqchip=off

Shots
-----
threshold-host-window.png      Threshold host window (first run)
threshold-host-second-run.png  Threshold host window (second run)
threshold-splash-view.png      In-app view of toh-boot-splash.GR (S key)

Numeric checks only (PIL); no screenshot was viewed in-model.
See pil_checks.txt for dimensions, palette indices, palette membership,
and header/icon/splash match scores.

Run evidence
------------
The app compiled from C:/Hermes/Apps/Threshold, ran twice, and returned
to a usable shell. ThresholdStatus wrote ThresholdStatus.TXT next to
the app with MOTD, pinned list, doors, art paths, and NEW lines.
