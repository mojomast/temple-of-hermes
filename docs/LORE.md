# The Codex of Nous - lore index (November 2026 refresh)

`Hermes/Lore/` is the guest-side Codex of Nous: a scrollable HolyC reader that
runs inside TinkerOS / THE TEMPLE OF HERMES. This file is the host-side index
for the same cards. It is the place to check a claim, a date, or a URL without
opening the guest.

The refresh is **2026-first**. Entries are paraphrases of first-party Nous
Research pages or first-party Nous Research posts on X. There are no fabricated
quotes, no invented dates, and no photoreal likenesses. The Temple of Hermes
itself is original flavor, not a Nous product and not a Nous claim.

Legend:

- **ORIGINAL** - Temple of Hermes flavor written for this project.
- **NEW** - added in the November 2026 refresh.
- **UPDATED** - an older card whose stale tense or missing source was fixed.
- **SOURCE** - first-party URL printed by the guest card.

## Cards in the guest Codex

### ORIGINAL - The Temple and the Codex

The Temple of Hermes is a public-domain TinkerOS fork built so a human and an
AI agent can share one virtual machine. The Codex is its reading room: a
guest-side index that keeps the temple's stories next to their sources. The
temple is not a Nous product and does not speak for Nous Research.

Guest file: `Hermes/Lore/Codex00.HC`.

### NEW - Arete-27B (6 Nov 2026)

Nous post-trained Alibaba's Qwen3.8-27B to reinforce Western values on a
Chinese-trained model. On an 803-prompt evaluation across seven value
categories, Arete-27B raised its fact score from 2.32 to 2.98 out of 5 and cut
answers containing propaganda from 22% to 1%, while staying close to base Qwen
on agentic benchmarks. The weights and the evaluation are open.

SOURCE: https://nousresearch.com/arete

Guest file: `Hermes/Lore/Codex01.HC`.

### NEW - A Note on Our Fundraise (7 Oct 2026)

Nous raised $90 million with NVIDIA, Microsoft's M12, Samsung, Robot Ventures,
Union Square Ventures, Y Combinator, and Menlo Ventures among others. The note
says the capital goes toward open, auditable AI and toward building Hermes for
Businesses.

SOURCE: https://nousresearch.com/a-note-on-our-fundraise

Guest file: `Hermes/Lore/Codex01.HC`.

### NEW - Refactoring Hermes with 1,393 agents (15 Sep 2026)

In a Teknium-bylined blog post, Hermes Agent refactored its own codebase: 1,393
subagents over about nineteen active hours cut non-test Python by 34.4%
(1,063,826 to 698,363 lines), for roughly $19,300 in model spend against a
$150k-$1.8M estimate for doing it by hand. The guest card is a paraphrase of
the blog post. It is **not** in-game Teknium dialogue and must not be read as
speech by an NPC.

SOURCE: https://nousresearch.com/refactoring-hermes-with-1393-agents

Guest file: `Hermes/Lore/Codex02.HC`.

### NEW - Hermes Agent (MIT release, February 2026)

Nous released Hermes Agent under the MIT license in February 2026; the Releases
page dates the release 25 Feb 2026. It runs where the user chooses, remembers
projects, writes reusable skills as it works, and carries that knowledge across
sessions. The October fundraise note says it has been cloned over 24 million
times.

SOURCES:

- https://nousresearch.com/releases
- https://hermes-agent.nousresearch.com/

Guest file: `Hermes/Lore/Codex02.HC`.

### NEW - Hermes Agent v0.23.0: The Hearth Release (5 Nov 2026)

The Hearth release brings the desktop into a browser tab, one gateway for every
conversation, `/Rewind`, group chats with automatic routing, spend limits for
paid tools, and a lighter, faster build.

SOURCE: https://x.com/NousResearch/status/2118479744979079669

Guest file: `Hermes/Lore/Codex03.HC`.

### NEW - Hermes Cloud agents in a browser tab (9 Nov 2026)

Hermes Cloud agents open in a browser tab with the same interface as Hermes
Desktop. Pick a name and a model in Nous Portal; Nous hosts the agent 24/7 in
its own container, so scheduled jobs and replies on any channel continue while
your laptop is closed. Plus, Super, and Ultra plans each include one Cloud
agent out of the box.

SOURCE: https://x.com/NousResearch/status/2119851439904510217

Guest file: `Hermes/Lore/Codex03.HC`.

### NEW - NousCoder-14B (6 Jan 2026)

A competitive olympiad programming model post-trained on Qwen3-14B via
reinforcement learning. Nous released the weights, an open RL environment and
eval harness, and W&B logs, and documented the pipelined verification setup and
parallelization.

SOURCES:

- https://nousresearch.com/nouscoder-14b-a-competitive-olympiad-programming-model
- https://huggingface.co/NousResearch/NousCoder-14B

Guest file: `Hermes/Lore/Codex04.HC`.

### NEW - Psyche: architecture and next phase (2025)

Psyche is open infrastructure for decentralized training across underutilized
hardware. Building on DisTrO and DeMo, it cuts data transfer by orders of
magnitude; the next phase coordinates work on Solana and aims to make
distributed training practical.

SOURCES:

- https://nousresearch.com/nous-psyche
- https://nousresearch.com/the-next-phase-of-psyche

Guest file: `Hermes/Lore/Codex04.HC`.

### NEW - Forge Reasoning API beta and Nous Chat (2025)

Nous launched the Forge Reasoning API beta and Nous Chat, a simple chat
platform featuring the Hermes language model. Forge packages Nous's
inference-time reasoning research.

SOURCE: https://nousresearch.com/introducing-the-forge-reasoning-api-beta-and-nous-chat-an-evolution-in-llm-inference

Guest file: `Hermes/Lore/Codex05.HC`.

### NEW - Atropos (2025)

Atropos is an RL environment framework designed to coordinate generation tasks
across potentially thousands of distributed workers, integrating with standard
inference APIs.

SOURCES:

- https://nousresearch.com/introducing-atropos
- https://github.com/NousResearch/atropos

Guest file: `Hermes/Lore/Codex05.HC`.

### UPDATED - Hermes 3 (August 2024)

Hermes 3 launched in August 2024 as the flagship of its generation: a 405B
model, smaller siblings, an open technical report, and a dataset. Later Hermes
4 and 4.3 followed, so Hermes 3 is not the current flagship. This card replaces
the stale "latest flagship" present-tense wording with a dated 2024 statement.

SOURCES:

- https://nousresearch.com/freedom-at-the-frontier-hermes-3
- https://nousresearch.com/releases

Guest file: `Hermes/Lore/Codex05.HC`.

## Deliberately not included

**No WorldSim origin card.** The only available recap was a LinkedIn post, and
that is not a first-party source. The Codex will add a WorldSim origin card
only when Nous publishes a first-party page for it. The existing WorldSim art
and icon remain art, not lore.

## Guest layout and heap budget

The live-CD compiler heap is small, so the reader is split into small includes.
Every `.HC` file in `Hermes/Lore/` stays well under the ~1.6 KB per-include
budget:

| File | Role | Bytes |
| --- | --- | --- |
| `Load.HC` | `Cd(__DIR__);;` + `#include "Codex";`; no side effects | 68 |
| `Run.HC` | includes `Load`, calls `CodexRun` | 41 |
| `Codex.HC` | includes the parts and the UI, defines `CodexRun` | 336 |
| `Codex00.HC` | title, reading key, ORIGINAL temple card | 1005 |
| `Codex01.HC` | Arete-27B, fundraise | 1075 |
| `Codex02.HC` | 1,393-agent refactor, Hermes Agent MIT card | 1243 |
| `Codex03.HC` | Hearth v0.23, Cloud agents in a browser tab | 1055 |
| `Codex04.HC` | NousCoder-14B, Psyche | 1141 |
| `Codex05.HC` | Forge, Atropos, Hermes 3 | 1367 |
| `Codex06.HC` | sources note + `LORE-RESULT.TXT` | 876 |
| `CodexUI.HC` | window, scroll bars, menu, read-only key loop | 615 |

`Load.HC` has no side effects. `Run.HC` is the only entry point that opens a
window. The reader runs in the caller task (so the window is already focused),
uses `SettingsPush` / `SettingsPop`, `MenuPush` / `MenuPop`, `DocScroll(TRUE)`
for scroll bars, and `DocTop` to start at the top. Arrow and page keys are
forwarded to the DolDoc cursor; printable keys are ignored, so the Codex stays
a reader. No child tasks are spawned, so there is nothing to `Kill` on exit;
`SettingsPop` restores the terminal when the reader closes.

The guest spells money as `USD 90 million`, `USD 19,300`, and `USD 150k-1.8M`.
A bare `$` in HolyC source starts a DolDoc command when the compiler reads the
file, so `USD` keeps the prose safe. The host copy below keeps the familiar
`$` glyphs.

The guest writes `::/Hermes/Lore/LORE-RESULT.TXT` (the boot drive's app
directory) with the card IDs it emitted. That is the agent-facing result file;
the verification never scrapes the bitmap for text.

## Verification (QEMU TCG)

Verified on TinkerOS 5.20-rc10 under QEMU TCG with
`-accel tcg -display none -nic none -machine pc,kernel-irqchip=off`:

- ISO SHA-256: `feb5cb570a79fefbefeb7d7a7133e3eac0e3b4ffcd6adf8a0fd29049476a1cc4`.
- The guest compiled `Hermes/Lore/Load.HC`, ran `CodexRun`, and wrote the
  result file with all card IDs (`original` through `hermes3-2024`).
- Screenshots live in `shots/hermes-lore/` (`01-codex-top.png` through
  `05-after-exit.png`).
- Checks are Python/PIL only: PNG size, palette indices 0-15, and a
  non-background bounding box. No screenshot is opened in-model.

## Source index

| Date | Card | Tag | Source |
| --- | --- | --- | --- |
| 9 Nov 2026 | Cloud agents in a browser tab | NEW | https://x.com/NousResearch/status/2119851439904510217 |
| 6 Nov 2026 | Arete-27B | NEW | https://nousresearch.com/arete |
| 5 Nov 2026 | Hearth v0.23 | NEW | https://x.com/NousResearch/status/2118479744979079669 |
| 7 Oct 2026 | A Note on Our Fundraise | NEW | https://nousresearch.com/a-note-on-our-fundraise |
| 15 Sep 2026 | Refactoring Hermes with 1,393 agents | NEW | https://nousresearch.com/refactoring-hermes-with-1393-agents |
| 25 Feb 2026 | Hermes Agent MIT release | NEW | https://nousresearch.com/releases |
| 6 Jan 2026 | NousCoder-14B | NEW | https://nousresearch.com/nouscoder-14b-a-competitive-olympiad-programming-model |
| 2025 | Psyche architecture / next phase | NEW | https://nousresearch.com/the-next-phase-of-psyche |
| 2025 | Forge Reasoning API beta / Nous Chat | NEW | https://nousresearch.com/introducing-the-forge-reasoning-api-beta-and-nous-chat-an-evolution-in-llm-inference |
| 2025 | Atropos | NEW | https://nousresearch.com/introducing-atropos |
| Aug 2024 | Hermes 3 | UPDATED | https://nousresearch.com/freedom-at-the-frontier-hermes-3 |

Checked 10 Nov 2026. All links are first-party Nous Research pages or Nous
Research posts on X.
