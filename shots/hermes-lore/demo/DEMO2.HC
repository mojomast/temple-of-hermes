// Compact demo: message of the day and the parlor-game oracle.
// Original fiction for THE TEMPLE OF HERMES.

U0 MOTD()
{
  CDateStruct ds;
  Date2Struct(&ds,Now+local_time_offset);
  LB("Message of the Day");
  "  $$WHITE$$%04d-%02d-%02d  %02d:%02d$$FG$$\n\n"
  ,ds.year,ds.mon,ds.day_of_mon,ds.hour,ds.min;
  "  A messenger is only as good as the road they remember.\n\n";
  "  $$LTGRAY$$Commands: Codex; Oracle; Capybara;$$FG$$\n";
}

U0 Oracle()
{
  LB("The Oracle of the Threshold");
  "  $$LTGRAY$$A parlor game, not divination or advice.$$FG$$\n\n";
  "  $$YELLOW$$The door you cannot see is the one you stand in.$$FG$$\n\n";
  "  $$LTGREEN$$Counsel:$$FG$$ Name the smallest next step.\n";
}
