# Credits

THE TEMPLE OF HERMES is a public-domain fork. It would not exist without:

- **Terry A. Davis**, who created TempleOS, HolyC, DolDoc, RedSea, and the
  original public-domain system this still is, in spirit and in most of the
  source. TempleOS remains public domain.
- **The TinkerOS authors** ([tinkeros/TinkerOS](https://github.com/tinkeros/TinkerOS)),
  who kept a TempleOS-compatible API while making the system more usable in
  QEMU (VMMouse, Comm, the VM installer, AHCI, and many fixes). This branch
  starts at TinkerOS 5.20-rc10. TinkerOS is released under the Unlicense.
- **ZealOS**, from which TinkerOS itself borrowed code (as its README already
  acknowledges).
- **Spirit** (und3f/temple-os-apps), the closest prior art for a TempleOS
  guest agent over serial (HolyC exec and clipboard). THE TEMPLE OF HERMES
  does not share Spirit's code, but the research notes credit the idea of a
  boot-time serial agent.

The Hermes daemon, exact text export, presence banner, event stream,
skip-install boot, and agent-aware safe-mode guards are new work in this
fork, also placed in the public domain under the Unlicense (see LICENSE).
