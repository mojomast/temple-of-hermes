// THE TEMPLE OF HERMES -- Lore Codex shared globals.
// Original flavor written for this fork (new). Sourced entries carry a
// public URL. See docs/LORE.md. No quotes are attributed to real people.

#define LORE_VERSION	"0.1.0"
#define LORE_TITLE	"CODEX OF NOUS"
#define LORE_REPO	"https://github.com/mojomast/temple-of-hermes"

U0 LoreRule()
{
  "$$CYAN$$----------------------------------------------------------------$$FG$$\n";
}

U0 LoreBanner(U8 *sub)
{
  "\n$$YELLOW$$  THE TEMPLE OF HERMES  $$CYAN$$/$$FG$$  %s  v%s\n"
  ,LORE_TITLE,LORE_VERSION;
  if (sub && sub[0])
    "  $$LTGREEN$$%s$$FG$$\n",sub;
  LoreRule;
}
