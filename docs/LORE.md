# THE TEMPLE OF HERMES — Lore Codex

The **Codex of Nous** is the in-guest lore layer for THE TEMPLE OF HERMES:
a small HolyC codex, a message of the day, a parlor-game oracle, and a few
temple easter eggs. It is original flavor for this fork, with every factual
claim about the outside world carrying a public URL.

It is **not** an official Nous Research artifact. THE TEMPLE OF HERMES is an
unaffiliated fork of TinkerOS / TempleOS. Nothing here is a statement, quote,
or endorsement by Nous Research, the TinkerOS authors, Terry A. Davis, or
Terry A. Davis' family.

## Canon rules

1. **Sourced claims have URLs.** The Codex prints the URL with the claim; the
   table below repeats them. URLs were checked on 2026-11-09.
2. **Original flavor is marked as new.** Entries tagged `ORIGINAL` are fiction
   written for this fork. They are never presented as research findings.
3. **No fabricated quotes.** No sentence is attributed to a real person. The
   only quoted material is website copy, explicitly attributed to the website,
   and paraphrased wherever possible.
4. **Fiction stays in the temple.** The Oracle is a parlor game, not
   divination, advice, or a prediction about any real person.

## Sourced claims

| # | Claim in the Codex | Source URL |
|---|---|---|
| 1 | Nous Research describes itself as a pioneer in open AI training and research, with a mission paraphrased here as proliferating open access to intelligence. | <https://nousresearch.com/> |
| 2 | Hermes 3 is described by Nous Research as the latest version of its flagship Hermes series; the 8B model card lists Meta Llama 3.1 8B as its base model and ChatML as its prompt format, and emphasizes alignment to the user. | <https://huggingface.co/NousResearch/Hermes-3-Llama-3.1-8B> |
| 3 | Nous Research published the Hermes 4 Technical Report as arXiv:2508.18255. | <https://arxiv.org/abs/2508.18255> |
| 4 | Hermes 4.3 was announced in December 2025 with context up to 512K, based on ByteDance Seed-OSS-36B-Base; Nous Research calls it the first production model post-trained entirely on the Psyche network. | <https://nousresearch.com/introducing-hermes-4-3/> |
| 5 | Psyche is described as a distributed training network using the DisTrO optimizer, communicating between nodes over the open internet, with consensus state managed on Solana. The Hermes 4.3 run averaged 144k tokens per second across 24 Psyche nodes. | <https://nousresearch.com/introducing-hermes-4-3/> |
| 6 | Nous Research maintains public organizations on GitHub and Hugging Face under the name `NousResearch`. | <https://github.com/NousResearch> · <https://huggingface.co/NousResearch> |
| 7 | In Greek myth, Hermes is the herald of the gods and a protector of heralds, travelers, thieves, merchants, and orators; winged sandals let him move between mortal and divine worlds, and he serves as a psychopomp. | <https://en.wikipedia.org/wiki/Hermes> |
| 8 | Psyche is a figure of classical mythology, the immortal wife of Cupid, often represented as a beautiful woman with butterfly wings. | <https://en.wikipedia.org/wiki/Psyche_(mythology)> |
| 9 | *Nous* is a Greek-derived word used in philosophy for the mind or intellect, the faculty of rationality or reason. | <https://en.wiktionary.org/wiki/nous> |
| 10 | The capybara is the largest living rodent, native to South American countries except Chile; it is a semiaquatic herbivore that lives near freshwater and feeds mainly on grasses and aquatic plants. | <https://en.wikipedia.org/wiki/Capybara> |
| 11 | THE TEMPLE OF HERMES is built on TinkerOS 5.20-rc10, a public-domain fork of TempleOS; TempleOS is public-domain work by Terry A. Davis. | <https://github.com/tinkeros/TinkerOS> · <https://templeos.org/> |

The Nous Research facts are deliberately narrow: the organization's own
self-description, the Hermes 3 model card, the Hermes 4 technical report, and
the Hermes 4.3 / Psyche announcement. Nothing here guesses at private
information, invents a quotation, or puts words in anyone's mouth.

## Original flavor (new for this fork)

Everything in this section is **ORIGINAL** and was written for THE TEMPLE OF
HERMES. It is not sourced from Nous Research or from any person.

- **The Temple of Hermes framing** — the temple, the columns, the messenger,
  the threshold, and the two-driver presence banner.
- **The Codex of Nous** — the in-guest index and its `ORIGINAL` entries.
- **The Oracle of the Threshold** — a parlor-game verse generator. Fiction
  only; not divination and not advice.
- **The Message of the Day** — twelve original lines rotated by the local date.
- **Cappy the capybara acolyte** — an original mascot character. The animal
  facts are sourced; the character is not a Nous Research mascot.
- **The Nous Girl badge** — an original fictional character, not a likeness of
  any real person and not an official Nous Research mascot.
- **The hidden latch (`Aletheia`)** — a small easter egg with no secret claim.

Visual counterparts live in `Hermes/Art/` (see `docs/ART.md`). The Psyche
neural-flower motif and the WorldSim globe are visual metaphors; the sourced
Psyche *network* facts are separate and appear above with their URL.

## Guest files

| Path | Role |
|---|---|
| `Hermes/Lore/Glbls.HC` | Shared banner, version, repository URL |
| `Hermes/Lore/Codex.HC` | `CLoreEntry` table, `Codex`, `CodexAll` |
| `Hermes/Lore/MOTD.HC` | `MOTD` and the original daily lines |
| `Hermes/Lore/Oracle.HC` | `Oracle` parlor game |
| `Hermes/Lore/Eggs.HC` | `Caduceus`, `Capybara`, `HermesFlight`, `NousGirl`, `Aletheia`, `LoreCommands` |
| `Hermes/Lore/Load.HC` | Include this to load the whole codex |
| `Hermes/Lore/Install.HC` | Copy hook; installs to `~/Lore` |
| `Hermes/Lore/README.TXT` | Plain-text guest readme |

## Commands

From a Temple of Hermes shell, after loading:

```holyc
Codex;                // index of every entry
Codex("hermes");      // one entry, with its source URL
CodexAll;             // print every entry
MOTD;                 // message of the day
Oracle;               // one parlor-game verse
Oracle("what now?");  // same, with the question echoed
Caduceus;             // messenger-staff ASCII
Capybara;             // Cappy and a sourced animal fact
HermesFlight;         // a small original scene
NousGirl;             // original badge notice
Aletheia;             // hidden latch
LoreCommands;         // command list
```

## Install hook (Once.HC is untouched)

The repository's `Once.HC` is **not modified** by this work. The lore ships a
separate `Install.HC` hook instead.

Load without installing (works from the source tree):

```holyc
#include "/Hermes/Lore/Load";
```

Install into the guest home directory, then load:

```holyc
#include "/Hermes/Lore/Install";
#include "~/Lore/Load";
```

Persistence without touching `Once.HC`: add one line to `~/HomeSys.HC` inside
`StartUpTasks` (or at the end of `~/Once.HC` if you choose to edit your own
guest copy):

```holyc
#include "~/Lore/Load";
```

The hook copies `Glbls.HC`, `Codex.HC`, `MOTD.HC`, `Oracle.HC`, `Eggs.HC`,
`Load.HC`, `Install.HC`, and `README.TXT` into `~/Lore`. It does not edit any
startup file.

## QEMU proof

The screenshots in `shots/hermes-lore/` were produced in this sandbox with
QEMU **TCG only** (`-accel tcg -display none -nic none -machine
pc,kernel-irqchip=off`). They use the public TinkerOS 5.20-rc10 live ISO and
QMP `screendump` PNGs; nothing is installed to a hard disk and `Once.HC` is
never touched.

- ISO: `TinkerOS_5.20-rc10.ISO` from
  <https://github.com/tinkeros/TinkerOS/releases/tag/5.20-rc10>
- SHA-256:
  `feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4`
- Guest path: the harness pushes three compact demo sources over COM1 into the
  live CD's writable `B:` RAM drive, then runs `#include "D1.HC";`,
  `#include "D2.HC";`, and `#include "D3.HC";`.

The canonical, full lore is `Hermes/Lore/*` and `Load.HC`. The live CD's
compiler heap is small, so the harness uses `shots/hermes-lore/demo/DEMO1..3.HC`
as compact on-screen renderings of the same entries: each include stays under
about 1.6 KB. The demo keeps the sourced URLs and marks original lines as new.

| Shot | Shows |
|---|---|
| `00-boot.png` | first-boot live CD before answering the installer |
| `01-after-install-prompt.png` | installer answered `NO` |
| `02-live-cd.png` | live CD shell, no install |
| `03-codex-index.png` | `Codex;` index with SOURCED / ORIGINAL tags |
| `04-codex-hermes.png` | Hermes entry with its Wikipedia URL |
| `05-codex-nous.png` | Nous Research entry with nousresearch.com |
| `06-motd.png` | `MOTD;` message of the day |
| `07-oracle.png` | `Oracle;` parlor-game verse |
| `08-capybara.png` | `Capybara;` and the sourced animal fact |
| `09-caduceus.png` | `Caduceus;` ASCII and the Hermes source URL |
| `10-aletheia.png` | `Aletheia;` hidden latch |

The harness `shots/hermes-lore/run_qemu.py` is self-contained and accepts
`TOH_TINKEROS_ISO` instead of a hard-coded host ISO path. It writes
`shots/hermes-lore/serial-transcript.txt` with the pushed sizes and acks.

## Licensing and credit

TempleOS is public domain by Terry A. Davis. TinkerOS is public domain under
the Unlicense. This fork keeps those notices. The lore source in
`Hermes/Lore/` is released with the rest of this repository under the same
public-domain terms; the sourced facts remain the property of their respective
publishers and are cited, not relicensed.
