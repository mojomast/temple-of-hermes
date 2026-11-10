// MESSAGE OF THE DAY -- original flavor for THE TEMPLE OF HERMES.
// Every line below is new fiction. None is a quotation from a real person.

U8 *motd_lines[]=
{
  "A messenger is only as good as the road they remember.",
  "The temple keeps no clock but the one you build.",
  "Bring a question; leave with a better question.",
  "Nine columns hold the roof. The tenth holds the door.",
  "The smallest acolyte carries the largest silence.",
  "A closed gate is still a lesson in patience.",
  "Write the map before you claim the country.",
  "Two drivers, one road: signal before you turn.",
  "The oracle is a game. The work is not.",
  "Old iron remembers every hand that warmed it.",
  "The codex grows by one page for every honest error.",
  "A wing is useful only after the fall is understood."
};

U0 MOTD()
{
  CDateStruct ds;
  I64 i,n=sizeof(motd_lines)/sizeof(U8 *);
  Date2Struct(&ds,Now+local_time_offset);
  LoreBanner("Message of the Day");
  "  $$WHITE$$%04d-%02d-%02d  %02d:%02d$$FG$$\n\n"
  ,ds.year,ds.mon,ds.day_of_mon,ds.hour,ds.min;
  i=(ds.year*1000+ds.mon*40+ds.day_of_mon)%n;
  "  %s\n\n",motd_lines[i];
  if (IsHypervisorPresent)
    "  $$LTGRAY$$The temple is running under a hypervisor.$$FG$$\n";
  "  $$LTGRAY$$Commands:$$FG$$ Codex;  Oracle;  MOTD;  LoreCommands;\n";
}
