// CODEX OF NOUS -- the lore index.
// SOURCED entries paraphrase public sources; the URL is printed with each.
// ORIGINAL entries are new fiction for this fork and are labelled as such.

class CLoreEntry
{
  U8 *slug;
  U8 *title;
  U8 *kind;
  U8 *body;
  U8 *url;
};

CLoreEntry lore_codex[]=
{
  {"hermes","Hermes, herald of the gods","SOURCED",
   "In Greek myth Hermes is the herald of the gods and a protector of heralds, travelers, thieves, merchants and orators. Winged sandals let him move between the mortal and divine worlds, and he also serves as a psychopomp, a guide of souls.",
   "https://en.wikipedia.org/wiki/Hermes"},

  {"psyche","Psyche of the butterfly wings","SOURCED",
   "Psyche is a figure of classical mythology, the immortal wife of Cupid, often represented as a beautiful woman with butterfly wings.",
   "https://en.wikipedia.org/wiki/Psyche_(mythology)"},

  {"nous","Nous, the word","SOURCED",
   "Nous is a Greek-derived word used in philosophy for the mind or intellect, the faculty of rationality or reason.",
   "https://en.wiktionary.org/wiki/nous"},

  {"capybara","The capybara","SOURCED",
   "The capybara is the largest living rodent and is native to South American countries except Chile. It is a semiaquatic herbivore that lives near freshwater and feeds mainly on grasses and aquatic plants.",
   "https://en.wikipedia.org/wiki/Capybara"},

  {"nous-research","Nous Research","SOURCED",
   "Nous Research describes itself as a pioneer in open AI training and research and states a mission to create and proliferate open access to intelligence. This codex paraphrases that self-description; it is not an endorsement of this fork.",
   "https://nousresearch.com/"},

  {"hermes-3","Hermes 3","SOURCED",
   "Nous Research describes Hermes 3 as the latest version of its flagship Hermes series of LLMs. The 8B model card lists Meta Llama 3.1 8B as the base model and ChatML as the prompt format, and emphasizes aligning the model to the user.",
   "https://huggingface.co/NousResearch/Hermes-3-Llama-3.1-8B"},

  {"hermes-4","Hermes 4 Technical Report","SOURCED",
   "Nous Research published the Hermes 4 Technical Report as arXiv:2508.18255.",
   "https://arxiv.org/abs/2508.18255"},

  {"hermes-4-3","Hermes 4.3 and Psyche","SOURCED",
   "Nous Research announced Hermes 4.3 in December 2025 with context up to 512K, based on ByteDance Seed-OSS-36B-Base. It calls Hermes 4.3 its first production model post-trained entirely on the Psyche network.",
   "https://nousresearch.com/introducing-hermes-4-3/"},

  {"psyche-network","The Psyche network","SOURCED",
   "Nous Research describes Psyche as a distributed training network that uses the DisTrO optimizer to communicate between training nodes over the open internet, with consensus state managed on Solana. The Hermes 4.3 run averaged 144k tokens per second across 24 Psyche nodes.",
   "https://nousresearch.com/introducing-hermes-4-3/"},

  {"nous-orgs","Nous Research on GitHub and Hugging Face","SOURCED",
   "Nous Research maintains public organizations on GitHub and Hugging Face under the name NousResearch.",
   "https://github.com/NousResearch  https://huggingface.co/NousResearch"},

  {"tinkeros","Built on TinkerOS and TempleOS","SOURCED",
   "The Temple of Hermes is built on TinkerOS 5.20-rc10, a public-domain fork of TempleOS. TempleOS is public-domain work by Terry A. Davis.",
   "https://github.com/tinkeros/TinkerOS  https://templeos.org/"},

  {"temple","The Temple of Hermes framing","ORIGINAL",
   "The Temple of Hermes framing, the Codex of Nous, the Oracle of the Threshold, the Message of the Day, the capybara acolyte and the temple easter eggs are original fiction created for this fork. They are not statements by Nous Research and do not imply affiliation or endorsement.",
   "https://github.com/mojomast/temple-of-hermes"},

  {"cappy","Cappy the capybara acolyte","ORIGINAL",
   "Cappy is an original capybara acolyte used as a calm mascot for this fork. The character is new; the real animal facts are sourced separately.",
   "https://github.com/mojomast/temple-of-hermes"},

  {"nous-girl","The Nous Girl badge","ORIGINAL",
   "The Nous Girl badge is an original fictional character drawn for this fork. It is not a likeness of any real person and is not an official Nous Research mascot.",
   "https://github.com/mojomast/temple-of-hermes"}
};

U0 Codex(U8 *slug=NULL)
{
  I64 i,n=sizeof(lore_codex)/sizeof(CLoreEntry);
  if (!slug || !slug[0])
  {
    LoreBanner("index");
    "  $$LTGRAY$$slug             kind      title$$FG$$\n";
    for (i=0; i<n; i++)
      "  $$LTGREEN$$%s$$FG$$\t$$YELLOW$$%s$$FG$$\t%s\n"
      ,lore_codex[i].slug,lore_codex[i].kind,lore_codex[i].title;
    "\n  $$LTGRAY$$Read one:$$FG$$ Codex(\"hermes\");"
    "  $$LTGRAY$$Read all:$$FG$$ CodexAll;\n";
    return;
  }
  for (i=0; i<n; i++)
    if (!StrICmp(slug,lore_codex[i].slug))
    {
      LoreBanner(lore_codex[i].title);
      "  $$YELLOW$$[%s]$$FG$$\n\n  %s\n\n"
      "  $$CYAN$$Source:$$FG$$ %s\n"
      ,lore_codex[i].kind,lore_codex[i].body,lore_codex[i].url;
      return;
    }
  "  No codex entry named %s. Try Codex;\n",slug;
}

U0 CodexAll()
{
  I64 i,n=sizeof(lore_codex)/sizeof(CLoreEntry);
  for (i=0; i<n; i++)
    Codex(lore_codex[i].slug);
}
