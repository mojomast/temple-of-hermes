// Bundled sample lore for Codex of Nous.
// This is deliberately short and clearly a sample.  When the image has
// Hermes/Lore/*.DD or *.TXT, Codex loads those files instead.

#define CX_SAMPLE_CNT 8

U8 *cx_sample_titles[CX_SAMPLE_CNT] =
{
  "The Messenger",
  "The Temple",
  "Nous",
  "The Codex",
  "The Caduceus",
  "The Capybara",
  "WorldSim",
  "The Art Branch"
};

U8 *cx_sample_bodies[CX_SAMPLE_CNT] =
{
  "The messenger crosses the threshold between the known and the\n"
  "unknown.  Wings at the heels, a staff in hand, a word carried from\n"
  "one house to another.\n"
  "\n"
  "In this temple the messenger is a pattern, not a person: the part\n"
  "of a system that listens, carries, and returns with an answer.\n",

  "A temple is a boundary made visible.  Columns hold a roof; a\n"
  "meander marks the edge; a doorway says that inside and outside are\n"
  "different places.\n"
  "\n"
  "The Temple of Hermes keeps that shape for a shared machine: a\n"
  "human and an agent at the same console, each able to see who is\n"
  "driving and what the other has done.\n",

  "Nous is mind, attention, the turning of thought toward a problem.\n"
  "It is drawn here as a neural flower: many paths, one center, no\n"
  "single path required.\n"
  "\n"
  "The Codex is a memory aid for such a mind.  It does not replace\n"
  "reading; it keeps the paths visible while you read.\n",

  "Codex of Nous has two panes.  The left pane lists entries.  The\n"
  "right pane shows the selected entry, wrapped to the window.\n"
  "\n"
  "Up and Down select.  PgUp and PgDn scroll.  Home and End jump.\n"
  "Enter reloads the lore directory.  Esc leaves the codex.\n"
  "\n"
  "If ::/Hermes/Lore exists, Codex reads *.DD and *.TXT from it.  If\n"
  "it does not, this bundled sample is shown instead.\n",

  "The caduceus is a staff with two serpents and a pair of wings.\n"
  "The serpents cross and separate; the wings stay open.  It is a\n"
  "sign of exchange, balance, and safe passage.\n"
  "\n"
  "The art in this tree draws it in the sixteen-color palette of the\n"
  "temple so that it reads at icon size as well as on a wall.\n",

  "The capybara is the temple pet: calm, social, and unimpressed by\n"
  "ceremony.  The art branch includes several poses for idle, sleep,\n"
  "wave, eat, dance, and the caduceus carry.\n"
  "\n"
  "Pets are a reminder that a shared machine is also a place where\n"
  "people spend ordinary time.\n",

  "WorldSim is the companion toy in this tree.  Five named agents\n"
  "wander a tile planet, gather resources, and write what they find\n"
  "into an event log.\n"
  "\n"
  "Space pauses the world, R grows a new one, Tab cycles agents, the\n"
  "arrow keys nudge the selected agent, and plus or minus changes the\n"
  "speed.  The worldsim icon is the same art used by this codex.\n",

  "The art branch is pictures and format tooling only.  It carries a\n"
  "sixteen-color palette, wallpapers, a splash, a UI strip, sprite\n"
  "sheets, and icons in 16, 32, and 64 pixel sizes.\n"
  "\n"
  "GR files are uncompressed device contexts.  SP files are CSprite\n"
  "streams.  Both are loaded with the ordinary TempleOS readers, so\n"
  "the same assets serve the desktop, the apps, and the boot screen.\n"
};

U0 CxLoadSample()
{
  I64 i;
  for (i=0;i<CX_SAMPLE_CNT;i++)
    CxAdd(StrNew(cx_sample_titles[i]),StrNew(cx_sample_bodies[i]),
          StrNew("bundled sample"));
}
