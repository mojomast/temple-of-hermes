# THE TEMPLE OF HERMES

A public-domain fork of [TinkerOS](https://github.com/tinkeros/TinkerOS) 5.20-rc10
(itself a fork of [TempleOS](https://templeos.org/) by Terry A. Davis) built so an
AI agent and a human can share one virtual machine, with **ground-truth** guest
state instead of screenshot OCR.

This branch is `hermes/v0`. The official bootable image is
`TempleOfHermes-0.1.0.ISO`, produced by TinkerOS's own `BootDVDIns` + `RedSeaISO`
path (see [`scripts/build_iso.py`](scripts/build_iso.py)).

> TempleOS is the work of Terry A. Davis and is public domain. TinkerOS is the
> work of its authors and is released under the Unlicense (public domain). This
> fork keeps those notices, keeps the Unlicense, and adds the Hermes guest
> daemon and co-use features. It is not affiliated with Terry's estate, the
> TinkerOS authors, or Nous Research.

## Why this exists

The [hermes-templeos](https://github.com/mojomast/hermes-templeos) plugin already
drives a stock TinkerOS VM over QMP (screen grabs, absolute mouse via VMMouse,
key injection) and a glyph OCR for `read_text`. That works, but the agent is
guessing: it cannot see the actual DolDoc text, does not know when a prompt is
waiting, shares one cursor with the user, and can wander into `Fmt` or
`OSInstall`. THE TEMPLE OF HERMES is a guest image that closes those gaps.

## What's new (never done in TempleOS / TinkerOS / ZealOS)

These were researched against stock TempleOS 5.03, TinkerOS 5.20-rc10, ZealOS,
TOSClient, Spirit (und3f/temple-os-apps), and temple-cua. Closest prior art is
**Spirit**, a boot-time guest agent that can exec HolyC and get/set the clipboard
over serial. Spirit does **not** export window text, stream window/task/prompt
events, show who is driving, skip the first-boot install/tour, or refuse
format/install while an agent is at the wheel.

Shipped in v0.1.0:

1. **Hermes agent daemon (HRPC)** — a structured request/reply/event channel on
   COM1 (115200 8n1) so the host can ping, eval HolyC, list tasks and windows,
   get or set focus and mouse state, dump text, switch driver mode, transfer
   files, and drain events, without OCR.
2. **Exact screen-text export** — dump the DolDoc *plain text* of the focused
   window or every visible window, with cursor coordinates, over serial. This
   is ground truth, not a glyph guess.
3. **Presence banner and a distinct agent cursor** — the wallpaper shows
   `THE TEMPLE OF HERMES [user|shared|agent]`. In AGENT or SHARED mode a second
   cyan/yellow crosshair marks the agent's pointer, separate from the user's
   black arrow.
4. **Event stream** — `ready`, `task_spawned`, `window_opened`,
   `prompt_waiting`, `compile_error`, `mode_changed`, `danger_blocked`, emitted
   as `HEVT` frames so the agent knows when the screen is idle or a prompt is
   up.
5. **Boot straight to the Hermes-ready state** — the live CD no longer asks to
   install or take the tour. Branding, wallpaper title, the daemon, and a
   serial `HBEACON TempleOfHermes/0.1.0` are there at first prompt.
6. **Safe-mode guards** — in AGENT mode, `YorN`, `AreYouSure`, `Fmt`,
   `OSInstall`, and `BootHDIns` refuse and emit `danger_blocked`. SHARED still
   allows ordinary `YorN` (the human can answer) but not format/install.

Implemented as part of the daemon but **not** claimed as a first: host/guest
clipboard (`clip_get` / `clip_set`). Spirit and TinkerOS TOSClient already did
clipboard over serial.

## Protocol (short)

On COM1, 115200 8n1, length-prefixed ASCII frames:

```
HBEACON TempleOfHermes/0.1.0
HREQ <id> <op> <len>\n + <len bytes of payload>
HRPL <id> <ok|err> <len>\n + <len bytes>
HEVT <seq> <kind> <len>\n + <len bytes of JSON>
```

Ops: `ping`, `eval`, `tasks`, `focus`, `mouse`, `text`, `mode`, `clip_get`,
`clip_set`, `list`, `pull`, `push`, `events`, `idle`, `help`.

Full research notes, comparisons, and the frame spec:
[docs/HERMES-FEATURES.md](docs/HERMES-FEATURES.md).

How the hermes-templeos plugin should grow a `hermes` flavor without adding a
fifth tool: [PLUGIN-INTEGRATION.md](PLUGIN-INTEGRATION.md).

## Build the ISO

QEMU and a copy of `TinkerOS_5.20-rc10.ISO` are required. Networking stays off.
The builder uses TinkerOS's own distro process inside the guest (`BootDVDIns`,
then `RedSeaISO`). On this project the box has no usable `/dev/kvm`, so the
build runs in TCG and takes a while.

```
# default stock ISO path used by hermes-templeos:
#   ~/.hermes/plugin-data/templeos/isos/TinkerOS_5.20-rc10.ISO
python3 scripts/build_iso.py
# writes dist/TempleOfHermes-0.1.0.ISO and dist/SHA256SUMS

python3 scripts/smoke.py
# screenshots + serial transcript in shots/
```

## Credits and license

See [LICENSE](LICENSE) (Unlicense / public domain) and [CREDITS.md](CREDITS.md).
Work in `Adam/Hermes`, the startup and branding changes, the kernel
`fp_input_gate` hook, and the host scripts are new in this fork.

---

# Upstream TinkerOS README

The text below is the upstream TinkerOS README, kept for credit and context.


<p align="center">
  <a href="https://tinkeros.github.io">
  <img src="https://tinkeros.github.io/Images/theme.gif" /></a>
</p>
<p align="center"><a href="https://tinkeros.github.io">TinkerOS/TempleOS documentation</a></p>
<p align="center"><a href="https://tinkeros.github.io/WbTempleOS/Downloads/">TempleOS downloads</a></p>
<p align="center"><a href="https://github.com/tinkeros/TinkerOS/releases">TinkerOS downloads</a></p>
<p align="center"><a href="https://github.com/tinkeros/TinkerOS/blob/main/LinuxQEMU.md">TempleOS/TinkerOS Linux QEMU VM setup guide</a></p>
<p align="center"><a href="https://github.com/tinkeros/TinkerOS/blob/main/WindowsQEMU.md">TempleOS/TinkerOS Windows QEMU VM setup guide</a></p>
<p align="center"><a href="https://github.com/tinkeros/TinkerOS/blob/main/Baremetal.md">TempleOS/TinkerOS baremetal (real hardware) setup guide</a></p>
</p>


### Preface
TinkerOS is essentially TempleOS renamed with some changes that allow it to run bare metal on some more modern machines since it "only" requires real or emulated PS/2 keyboard and mouse input and legacy boot support, but does not require legacy / IDE disk support. Though some improvements and bug fixes are added to TinkerOS, 95% of the code is the same as TempleOS and TinkerOS can install and compile TempleOS.  TempleOS on the other hand requires hardware which supports Terry's hard coded 640x480 video mode which has been deprecated on some newer machines.  Also TempleOS requires an IDE drive interface or legacy ATA SATA support.  TinkerOS supports AHCI SATA mode installation.  It also has a "Live USB" version which runs from a RAM disk which allows it to be tried without installing or run on systems without supported drives.  You can also use the USB version to install it on supported machines that do not have a CD/DVD drive.  If your machine uses the newer EFI boot method, it will still need to support legacy booting (via CSM) which you may need to turn on in your BIOS.  

### Goals
- Keep a TempleOS like look and feel while attempting to keep a fully TempleOS compatible API to the maximum extent possible.  TinkerOS should always be able to compile and install TempleOS.
- Be a fun playground OS that you can run on older machines 64-bit machines and do useful things with the serial and parallel ports.
- Live USB boot (use .img, not .iso files) allows booting TempleOS/TinkerOS to RAM disk to try it without having to install it on many machines.  These even work on some systems lacking legacy storage support.  The live boot version also contains utilities to help with baremetal installation on real hardware.
- Cleanup some unfortunate language that was left in TempleOS.
- Bring back some old TempleOS features and add new features, popular apps, and games.
- Make higher resolutions easy to setup.
- Make more colors available for TinkerOS features and 3rd party apps.  The original TempleOS code that makes use of only 16 colors still works, no backward compatability has been broken.  TempleOS uses colors 16 colors 0-15 and 255=transparent.  TinkerOS and 3rd party apps can additionally use colors 16-254 for 239 more colors to work with.  These can be any 24-bit RGB color.
- Make most apps and games work and look decent on both 4:3 and widescreen monitors using letterboxing for a 4:3 experience or scaled widescreen modes with an effective width of 640 (640x360, 640x400, 640x512)
- Improve installation process.
- Possibly new device driver support for modern storage and/or networking.
- Document bare-metal device compatability.  Please make a pull request to update Compatibility.csv if you want to help.

### Notes
- TempleOS and TinkerOS have no device drivers for CPU frequency control, temperature detection, fans, or other motherboard devices.  It may be the case that you are able to boot TinkerOS bare metal, but you may be putting your machine at risk and it may crash due to thermal issues or because a watchdog timer is tripped because the operating system does not take over control of critical hardware (since there is no driver for it).  There are no plans to fix this, if you system has these issues your only option is to run it inside a virtual machine instead of bare metal or to implement the required drivers yourself.
- Though only 16 colors are typically used at a time, the graphics mode is 32-bit.  The frame buffer is linear and has resolution FB_WIDTH by FB_HEIGHT which maybe larger than GR_WIDTH and GR_HEIGHT.  You can always suspend the window manager and draw whatever graphics you want instead.  text.fb_alias is a pointer to the frame buffer.
- Many laptops have keyboards and trackpads which are not PS/2 compatible (this is especially true of ultra thin laptops and chromebooks).
- ISOs files will not boot from USB not matter what tool you use to write them to a USB stick.  If you want to boot from USB you must use the .img file instead.


### Acknowlegements
- Terry Davis for <a href="https://templeos.org/">TempleOS</a> of course!
- Code ported from <a href="https://github.com/Zeal-Operating-System/ZealOS">ZealOS</a>.

