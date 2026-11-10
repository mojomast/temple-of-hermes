// THE ORACLE OF THE THRESHOLD -- a parlor game, not divination.
// All verses and counsel are original fiction written for this fork.

U8 *oracle_verses[]=
{
  "The door you cannot see is the one you are standing in.",
  "A borrowed lamp shows the road, not the destination.",
  "Count the stones twice; lay the third one true.",
  "The river answers the bridge, never the shout.",
  "What the wind forgets, the root remembers.",
  "A key is a promise with teeth.",
  "The map is honest; the traveler is tired.",
  "Two wings, one sky, and no schedule at all.",
  "The quiet room is full of unfinished doors.",
  "Every threshold is a small argument with gravity.",
  "The serpent is not the staff, but it knows the way.",
  "A seed is a rumor that the ground believes."
};

U8 *oracle_counsel[]=
{
  "Name the smallest next step and take only that.",
  "Ask what you are protecting before you optimize.",
  "Write down the assumption you are least willing to test.",
  "Leave one path unclaimed so the next traveler has work.",
  "Measure twice, but do not measure forever.",
  "Say the hard thing plainly and then stop talking.",
  "Rest is part of the route, not a detour from it.",
  "When two maps disagree, walk the edge between them.",
  "Keep the tool that can be repaired.",
  "Make the handoff legible to a stranger.",
  "Prefer the question that survives your favorite answer.",
  "Close one door today so the room can be used."
};

U0 Oracle(U8 *question=NULL)
{
  I64 i,j;
  I64 nv=sizeof(oracle_verses)/sizeof(U8 *);
  I64 nc=sizeof(oracle_counsel)/sizeof(U8 *);
  LoreBanner("The Oracle of the Threshold");
  "  $$LTGRAY$$A parlor game for the temple. This is not divination, not$$FG$$\n";
  "  $$LTGRAY$$advice, and not a statement by Nous Research or any real$$FG$$\n";
  "  $$LTGRAY$$person. All lines are original fiction.$$FG$$\n\n";
  if (question && question[0])
    "  $$WHITE$$You ask:$$FG$$ %s\n\n",question;
  i=RandU32%nv;
  j=RandU32%nc;
  "  $$YELLOW$$%s$$FG$$\n\n",oracle_verses[i];
  "  $$LTGREEN$$Counsel:$$FG$$ %s\n\n",oracle_counsel[j];
  "  $$LTGRAY$$The Oracle answers with fiction only.$$FG$$\n";
}
