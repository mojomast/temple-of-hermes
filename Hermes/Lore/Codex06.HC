U0 CodexPart6()
{
  U8 *res;
  DocPrint(NULL,
    "$FG,8$------------------------------------------------------------$FG$\n"
    "$FG,14$Sources and notes$FG$\n"
    "Every card above prints its first-party URL. X links are Nous Research's\n"
    "own posts. The host copy at docs/LORE.md repeats the same links.\n"
    "No WorldSim origin card is included: no first-party page exists yet.\n"
    "No fabricated quotes; the 1,393-agent card is a blog paraphrase, not\n"
    "in-game Teknium dialogue. Colors use the TempleOS 16-color palette.\n"
    "$FG,7$Guest build: Hermes/Lore. Host index: docs/LORE.md.$FG$\n\n"
  );
  res="LORE OK\noriginal\narete-27b\nfundraise-90m\nrefactor-1393\n"
      "hermes-agent-mit\nhearth-v0.23\ncloud-browser\nnouscoder-14b\n"
      "psyche\nforge\natropos\nhermes3-2024\n";
  FileWrite("::/Hermes/Lore/LORE-RESULT.TXT",res,StrLen(res));
}
