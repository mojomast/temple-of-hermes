# TOH-INT integration record

This file records the Temple of Hermes integration branch
`hermes/integration`: its base, every accepted branch and SHA that was
merged, the conflicts and decisions, and the evidence produced for the
deliverables. No plugin branch was merged into this tree.

## Base

- Branch: `hermes/art-nous`
- Tip: `fdb2f54fa22cdaabb088e6b04b2c74e4c80cccc6`
  (`feat(art): cinematic Nous Girl splash and character temple portraits`)
- Parent line: `hermes/art` `97d7ad285ea9942aacf87c50f41927c8c6eae88a`,
  `hermes/v0` `df91dbc5a173d3796ba3c581ebe99fac44582789`, TinkerOS
  5.20-rc10 `b8d1703`.
- The integration branch was created with
  `git checkout -B hermes/integration fdb2f54fa22cdaabb088e6b04b2c74e4c80cccc6`
  after `git fetch origin`. The sandbox initially had no remote configured;
  `origin` was added as the public `temple-of-hermes` remote and fetched
  before the reset.

Official art-nous assets verified in the base tree:

| Asset | Size |
| --- | --- |
| `Hermes/Art/UI/header-dojo-plate.GR` | 102432 bytes (640x160) |
| `Hermes/Art/UI/header-southpaw-plate.GR` | 102432 bytes (640x160) |
| `Hermes/Art/Icons/{16,32,64}/teknium.GR` | 288 / 1056 / 4128 bytes |
| `Hermes/Art/Icons/{16,32,64}/southpaw.GR` | present |
| `Hermes/Art/Sprites/toh-nous-girl.SP` | present |
| `Hermes/Art/Wallpaper/toh-nous-girl.GR`, `Hermes/Art/Splash/toh-boot-splash.GR` | present |

No stand-in `.GR` file was invented.

## Accepted branches merged

Every row was merged after the base reset. The merge commit is in
`hermes/integration`; the tip SHA is the accepted branch tip used for the
merge.

| Branch | Accepted tip SHA | Merge commit |
| --- | --- | --- |
| `hermes/apps` (B2) | `4dabe29456b5b3d5bcd933ae16763c4e0e13e7d4` | `a636f022abfc6205ab5b147b805b4891bd051c6c` |
| `hermes/lore2` (B6 refresh) | `064d70fdcd6ad5e873d8b56ccc2a4fbe41360455` | `4cae5a468fb7f895ec34ef498b2c17c77ac56157` |
| `hermes/app-threshold` | `9b5d07baaf3f3ae3c252f8263e151f52fcc2fd5a` | `b85c7f98a829e519f09403b04e3206ba87cd2a3c` |
| `hermes/app-offerings` | `adeed21b83de2270de20304b50ceaf240ae2071e` | `277858c4fd47a55f6b95159f299af3a60f10b3ce` |
| `hermes/app-dojo` | `1a09702b78520f78c07352d0e3f2d850bf69190d` | `53b916195e8ed9cab3512e8244a3aa8e3e848b5e` |
| `hermes/app-southpaw` | `a9ec1eeec31728d462c3fa5a3d6345c24a4c7412` | `46afb7220b0401941a0a3392cf4ac9e12e1644af` |
| `hermes/app-hermeschat` (B4) | `a87c6934554fe07762aad25938d398f657e22126` | `66459e33168109bc12f27b6e4ab95552f9b68bc1` |
| `hermes/app-worldsim` (B7) | `2e7c96108e2cfec05f05fde7c11f4ab82050c108` | `8ae16158a8a55c433617155e8e3a310d75642db9` |
| `hermes/app-psyche` (B8) | `e9c6e63124384fe108beeb1fd366d071bc1a1845` | `0c8f2c7c6f6036e167a3ba9520e4619b95da3c9e` |
| `hermes/app-messengerrun` (B9) | `184771131ce497110e491bad3ad2752297102400` | `f4e1e8119480a607d011391aa82e49fdc2bbab97` |
| `hermes/app-bbs` (BBS-GUEST) | `f58f42a177bdf5a9603687920e98554265f7ff2c` | `8bfffc980425c92cfe1cc942fd9cef5fbf8d500f` |
| `hermes/qemu-probe` (B0) | `162e8cf35604333868e604178d898cd46a2c5c31` | `699464a9bdffe694c780282783c7f8193ef921af` |
| `hermes/art-verify` (TOH-ART) | `688aadcf8bde5b13015c8ecad2fd6c30ddfd030f` | `e4471de3977060ee12075acfddc79422151ebbd1` |
| `hermes/holyc-guide` (B1) | `482269b0968c7ff4dd4fd7b93b477c5ef91f5737` | `a076ca7ab4143de59a0280f22ffcfec7ad2ae5a4` |
| `hermes/net` (B3) | `41963802b1f224a438801dd3f5459145abdbbd94` | `4121e170c7240b19f070fef3ef2cb48d585ab3b9` |
| `hermes/tools` (B5) | `15e4a1798732e10c9ac1f4394092dd0e49f1b469` | `53ba66bfec07430eb44499b8690a924ef92b4232` |
| `hermes/rebrand` (TOH-REBRAND) | `5f6ca3ae34307c7d9bb4686800b974b9348c0fd6` | `4a6de6f5a3c63f020fc2f7d6a3ddc51ca6abd38f` |
| `hermes/bbs-contracts` | `7feeba696da7b1b4e3df0efc9bf32cfb223f8581` | `129c80b3d01da2759319395ab968df3368aac121` |
| `hermes/bbs-server` | `74b4b44133373ee905cacd4afd2665e0484c1407` | `ceadbfef6b531c89194d0887a70c0ae8093ea973` |
| `hermes/lore` (B6) | `fb7f7ca63ea36401f9d100bbf4570a272087277c` | ancestor of `hermes/lore2`; merged with it |
| `hermes/art` (TOH-ART base) | `97d7ad285ea9942aacf87c50f41927c8c6eae88a` | ancestor of `hermes/art-nous` |

`hermes/app-southpaw` was absent on the first fetch. A final `git fetch`
found the complete app and shots at
`a9ec1eeec31728d462c3fa5a3d6345c24a4c7412`; it was merged and registered as
a real `planned = FALSE` app.

## Merge decisions

- **B2 first.** `hermes/apps` established `Hermes/Apps/Registry.HC`,
  `Launcher/`, `Common/`, the `Once.HC` autostart, and the README. Later app
  branches add real `Run.HC` files; the registry was then rewritten in this
  integration pass so accepted apps are `planned = FALSE`.
- **lore2 supersedes lore.** `hermes/lore2` contains `hermes/lore`
  (`fb7f7ca`) and adds the November 2026 Codex refresh. `Hermes/Lore/Load.HC`
  now includes only `Codex` (`Codex00`-`Codex06` and `CodexUI`).
- **BBS guest registry/README.** `hermes/app-bbs` added its own copy of the
  B2 registry and README. The merge kept the B2 versions for the framework
  and the final registry edit adds the `hermes-bbs` entry with its real
  `::/Hermes/Apps/HermesBBS/Run.HC` path.
- **Net sources.** `hermes/app-hermeschat` carried a private copy of
  `Hermes/Net`; `hermes/net` (B3) is the canonical implementation. The four
  conflicting Net sources were resolved to B3, while the extra
  `Hermes/Net/Build.HC` compile check from the chat branch was kept.
- **Rebrand docs.** `hermes/rebrand` carried copies of the B1 HolyC guide and
  the B0 QEMU probe. The dedicated branches' versions were kept for
  `docs/HOLYC-BEST-PRACTICES.md` and `docs/QEMU-SANDBOX-PROBE.md`; the
  rebrand's own `docs/REBRAND.md`, upstream docs, install prompts, `Once.HC`
  and kernel strings were merged.
- **No plugin merge.** Branch `feat/plugin-integration`
  `d8a7ee33bd15b296dedfa23c5948b4cad27c8e1c` is cited for the chat bridge,
  guest ops, Terry, and BBS transport skill. No plugin branch
  (`feat/plugin-integration`, `feat/improvements`, `feat/terry-*`,
  `feat/p3-guest-ops`, `feat/bbs-transport`, `feat/bbs-skill`) was merged
  into this tree.

## MakeDistro

`Adam/Hermes/MakeDistro.HC` now:

- `CopyTree("/Hermes","/Distro/Hermes")` after `/Doc`, so the disc carries
  `Hermes/Apps`, `Hermes/Art`, `Hermes/Net`, `Hermes/Lore`, and the rest.
- Keeps `CopyTree("/Home")`, `/Adam`, `/Apps`, `/Compiler`, `/Demo`, `/Doc`,
  `/Kernel`, `/Misc`, `/Downloads`, and the boot files.
- Applies the REBRAND request without editing `MakeDistro` elsewhere.
  `TempleSetISOLabel()` patches the ISO9660 primary and supplementary Volume
  Identifier fields to `THE_TEMPLE_OF_HERMES` immediately after
  `RedSeaISO`. The requested string is used verbatim; the filename remains
  `TempleOfHermes-0.1.0.ISO`.
- The B2 `Once.HC` autostart (`HermesStartApps`) is part of the merged tree
  and runs the launcher after the existing welcome text.

## Registry and apps

`Hermes/Apps/Registry.HC` has real `planned = FALSE` entries and working
`::/Hermes/Apps/<App>/Run.HC` paths for:

| App | Run path | Icon |
| --- | --- | --- |
| Hermes Chat | `HermesChat/Run.HC` | `hermes-chat` |
| WorldSim | `WorldSim/Run.HC` | `worldsim` |
| Codex | `Codex/Run.HC` | `codex-of-nous` |
| Psyche | `Psyche/Run.HC` | `psyche` |
| Capybara | `Capybara/Run.HC` | `capybara-pet` |
| Messenger Run | `MessengerRun/Run.HC` | `messenger-run` |
| Hermes BBS | `HermesBBS/Run.HC` | `modem-net` |
| Threshold | `Threshold/Run.HC` | `home-temple` |
| Dojo | `Dojo/Run.HC` | `teknium` |
| Offerings | `Offerings/Run.HC` | `don-piedro` |
| Southpaw | `Southpaw/Run.HC` | `southpaw` |
| Modem / Net | `Net/Run.HC` (no Run.HC yet) | `modem-net` (planned) |

`home-temple` and `nous-girl` open the launcher status panels instead of a
separate app. All icons are existing files under `Hermes/Art/Icons`; no art
was regenerated.

## Codex lore

`Hermes/Apps/Codex/Codex.HC` reads `::/Hermes/Lore/*.DD` and
`::/Hermes/Lore/*.TXT` at startup. After the lore2 merge the refreshed
content is present as:

- native guest reader: `Hermes/Lore/Codex00.HC` through `Codex06.HC`,
  `CodexUI.HC`, loaded by `Hermes/Lore/Load.HC`;
- plain-text export: `Hermes/Lore/Codex.TXT`, copied from the refreshed
  `docs/LORE.md`.

The bundled sample in `Hermes/Apps/Codex/CodexLore.HC` is only a fallback
when the lore directory is absent or empty.

## Lore2 leftover cleanup

Deleted only after confirming the new `Hermes/Lore/Load.HC` does not include
or launch them, and that no merged source references them:

- `Hermes/Lore/Eggs.HC`, `Glbls.HC`, `Install.HC`, `MOTD.HC`, `Oracle.HC`,
  `README.TXT`;
- old B6 shots `shots/hermes-lore/00-boot.png`,
  `01-after-install-prompt.png`, `02-live-cd.png`, `03-codex-index.png`,
  `04-codex-hermes.png`, `05-codex-nous.png`, `06-motd.png`, `07-oracle.png`,
  `08-capybara.png`, `09-caduceus.png`, `10-aletheia.png`;
- old B6 `shots/hermes-lore/demo/DEMO1-3.HC`, `run_qemu.py`,
  `serial-transcript.txt`, and the old shot README.

Kept: the new lore2 shots `01-codex-top.png`, `02-codex-2026.png`,
`03-codex-hermes.png`, `04-codex-sources.png`, `05-after-exit.png` and the
new Codex source files. `shots/hermes-lore/README.md` was rewritten to
describe the retained refresh shots.

## Dojo official art swap

`hermes/app-dojo` shipped substitutes because its sandbox lacked art-nous.
After the base reset:

- deleted `Hermes/Apps/Dojo/header-dojo-plate.GR` (640x64, 40992 bytes),
  `teknium-icon.GR`, and `dojo-icon.GR`;
- `DojoTask.HC` loads the official `Hermes/Art/UI/header-dojo-plate.GR`
  (640x160) and `Hermes/Art/Icons/64/teknium.GR`, falling back to the
  32-pixel teknium icon if the 64 is absent;
- `DojoUtil.HC` resolves guest art under `::/Hermes/Art`, `T:/Hermes/Art`,
  `C:/Hermes/Art`, or `~/Hermes/Art`;
- `DojoPaint.HC` was re-laid out for the taller 160-pixel plate (panels start
  at y=168, bottom controls at y=400) so the official plate is not covered.

No face was redrawn and no substitute mascot text was added.

## TinkerOS registry key migration

Only `Hermes/Apps/MessengerRun` used a leftover `TinkerOS/*` key.
`MessengerRun.HC` now writes `TempleOfHermes/MessengerRun`. On first run it
prefers the new key; if the new key is absent it executes the old
`TinkerOS/MessengerRun` key, copies `mr_best` into the new key, then uses the
new key. The README documents the migration. Stock upstream `Apps/`,
`Demo/`, and game keys were not rewritten.

## Chat relay bridge

`host/hermes_chat_relay.py` adds `HermesAgentResponder`. Its `reply(text)`
lazily calls the plugin-side PINT2 hook `templeos.chat_bridge` from
`feat/plugin-integration` `d8a7ee33bd15b296dedfa23c5948b4cad27c8e1c`. If the
plugin is absent, the bridge is disabled/unset/has no endpoint, or the agent
raises, it falls back to the deterministic offline `HermesResponder`.
Configuration is env-only through the plugin contract
(`TEMPLEOS_CHAT_BRIDGE`, `TEMPLEOS_CHAT_BRIDGE_ENDPOINT`,
`TEMPLEOS_CHAT_BRIDGE_TOKEN`, `TEMPLEOS_CHAT_BRIDGE_TIMEOUT_S`); no URL,
host, socket path, or token is hardcoded in code or docs. Payload bytes stay
out of logs unless `log_messages=True` is explicitly passed. Tests inject a
fake bridge and stay fully offline. The contract is documented in
`docs/HERMES-CHAT-PROTOCOL.md`.

## Shots

`shots/hermes-integration/` has the built-disc evidence:

| File | Evidence |
| --- | --- |
| `00-boot-splash.png` | boot splash |
| `01-home-launcher.png` | home screen with 14/14 real art icons and the launcher |
| `10-hermes-chat.png` | Hermes Chat UI, `connected: CONNECT hermes`, icon loaded |
| `11-worldsim.png` | WorldSim map and event line |
| `12-codex.png` | Codex of Nous reader |
| `13-psyche.png` | Psyche DisTrO view |
| `14-capybara.png` | Capybara pet |
| `15-messenger-run.png` | Messenger Run arcade |
| `16-hermes-bbs.png` | Hermes BBS local compile/fallback state (no server deploy) |
| `17-threshold.png` | The Threshold, including its PINNED list |
| `18-dojo.png` | Teknium's Dojo with the official 640x160 plate |
| `19-offerings.png` | Don Piedro's Offerings, `Spoons only. No real money.` |
| `20-southpaw.png` | Southpaw announcer view |

`shots/hermes-tools/` has the B5 RPC evidence from a fully booted guest:
`20-tools-toast.png`, `21-tools-windows.png`, `22-tools-guards.png`,
`23-tools-sysinfo.png`, with the exact JSON in `tools.json`. The RPCs
returned `ping` ok, `toast` ok, `windows` ok, `guards` with
`allow=0` and `blocked` = Fmt/AreYouSure/OSInstall/BootHDIns, and `sysinfo`
with version 0.1.0, 640x480, COM1 115200. The COM1 socket must be drained
continuously from boot; the harness does that in a reader thread so the
guest serial buffer never backs up.

Every image is checked with Python/PIL only: 640x480, palette indices 0-15
(or a 16-entry EGA mapping), unique-color count, and non-black bbox. No image
was opened for visual inspection. All QEMU runs use TCG and the sandbox-safe
flags:

```
-accel tcg -display none -nic none -machine pc,kernel-irqchip=off
```

The reproducible build path is
`shots/hermes-integration/build_from_installed.py`: it boots the stock
5.20-rc10 live CD, mounts the installed disk and a FAT32 overlay, runs
`#include "D:/RUN.HC"`, then runs
`#include "C:/Adam/Hermes/MakeDistro"`. The resulting ISO is 13,938,688 bytes
(`blkid` reports `LABEL="THE_TEMPLE_OF_HERMES" TYPE="iso9660"`). The exact
final SHA-256 was redacted from the sandbox event log (prefix `ca1e854`);
the checksum file recovered from the last pre-success snapshot is
`dist/SHA256SUMS`. The guest `Dir("T:/Hermes")` listing and `Art icons: 14/14`
prove the tree is on the disc. Every boot/wait is bounded; image checks are
Python/PIL only (size, palette indices 0-15, bbox), never visual inspection.

`scripts/build_iso.py` was adjusted to handle the real TinkerOS install
prompts (`Reboot Now` instead of a non-existent `Press a key`) and
`scripts/qemu_hermes.py` was made sandbox-portable with an optional
`TOH_TINKEROS_ISO` override.

## Open issues

- Push credentials are not available in this sandbox: the branch is
  committed locally, but `git push origin hermes/integration` fails with
  `could not read Username for 'https://github.com'`. No force-push, tag, or
  push to `main`/`hermes/v0` was attempted. Re-run the push from an
  authenticated host.
- `modem-net` has no `Hermes/Apps/Net/Run.HC`; it remains planned.
- The Hermes BBS app is locally buildable and registered, but the UI cannot
  reach a server because this task forbids deploying the BBS or contacting a
  VPS. The booted shot shows the local compile/fallback state; no server was
  started and no hostname was configured.
- Southpaw is merged and registered as `planned = FALSE`, and its branch
  shots are in `shots/hermes-app-southpaw/`. On this integrated ISO the
  in-guest compiler reports `Char const limited to 8 chars` while parsing
  `Hermes/Apps/Southpaw/View.HC`; `20-southpaw.png` is the booted error state.
  The app code and official icons are present; this needs a HolyC lexer fix
  before the view renders in the integrated image.
- The B5 shots in `shots/hermes-tools/` are refreshed from this integrated
  guest, not reused as proof of the older standalone branch.
