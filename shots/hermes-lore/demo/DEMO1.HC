U0 LB(U8 *s)
{
  "\n$$YELLOW$$THE TEMPLE OF HERMES$$FG$$ / $$CYAN$$CODEX OF NOUS$$FG$$\n";
  if (s && s[0]) "$$LTGREEN$$  %s$$FG$$\n",s;
  "$$CYAN$$----------------------------------------------$$FG$$\n";
}

U0 Codex(U8 *s=NULL)
{
  if (!s || !s[0])
  {
    LB("index");
    "  $$LTGREEN$$hermes$$FG$$       SOURCED   herald of the gods\n";
    "  $$LTGREEN$$psyche$$FG$$       SOURCED   butterfly wings\n";
    "  $$LTGREEN$$nous$$FG$$         SOURCED   mind or intellect\n";
    "  $$LTGREEN$$nous-research$$FG$$ SOURCED  open AI research\n";
    "  $$LTGREEN$$capybara$$FG$$     SOURCED   the largest rodent\n";
    "  $$LTGREEN$$temple$$FG$$       ORIGINAL  this fork's fiction\n";
    return;
  }
  if (!StrICmp(s,"hermes"))
  {
    LB("Hermes, herald of the gods");
    "  $$YELLOW$$[SOURCED]$$FG$$ In Greek myth Hermes is the herald of\n";
    "  the gods and a protector of travelers, thieves and orators.\n";
    "  $$CYAN$$Source:$$FG$$ https://en.wikipedia.org/wiki/Hermes\n";
  }
  else if (!StrICmp(s,"nous-research"))
  {
    LB("Nous Research");
    "  $$YELLOW$$[SOURCED]$$FG$$ Nous Research describes itself as a\n";
    "  pioneer in open AI training and research.\n";
    "  $$CYAN$$Source:$$FG$$ https://nousresearch.com/\n";
  }
  else if (!StrICmp(s,"temple"))
  {
    LB("The Temple of Hermes framing");
    "  $$YELLOW$$[ORIGINAL]$$FG$$ The temple, the Codex and Cappy are\n";
    "  new fiction for this fork, not Nous Research statements.\n";
  }
  else
    "  No codex entry named %s. Try Codex;\n",s;
}
