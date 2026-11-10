#ifndef DOJO_POP_HC
#define DOJO_POP_HC
#include "DojoUtil.HC"
U0 DojoShowResult(I64 n)
{
  U8 *b=DojoResultText(n);
  CTask *pu=NULL;
  if (!b)
    b=StrNew("No result yet.\nRun the challenge first.\n");
  PopUp(b,Fs,&pu);
  if (TaskValidate(pu)) Kill(pu);
  Free(b);
}
U0 DojoPlaque()
{
  CTask *pu=NULL;
  U8 *st=
  "$$WW,1$$$$YELLOW$$HERMES DOJO WALL PLAQUE$$FG$$\n\n"
  "Teknium appears only as Kyle's game character.\n"
  "Trainer voice from the game: \"Ship first, patch later.\"\n\n"
  "NousCoder-14B:\n"
  "$$TX,\"https://nousresearch.com/nouscoder-14b-a-competitive-olympiad-programming-model\","
  "HTML=\"https://nousresearch.com/nouscoder-14b-a-competitive-olympiad-programming-model\"$$\n\n"
  "HolyC best practices: docs/HOLYC-BEST-PRACTICES.md\n"
  "Read it before you patch the temple.\n";
  PopUp(st,Fs,&pu);
  if (TaskValidate(pu)) Kill(pu);
}
U0 DojoReport()
{
  CTask *pu=NULL;
  U8 *st=MStrPrint(
  "$$WW,1$$$$YELLOW$$DOJO SCORE REPORT$$FG$$\n\n"
  "1 Caduceus ...... %s %d\n"
  "2 DolDoc form ... %s %d\n"
  "3 draw_it sprite  %s %d\n"
  "4 File echo ..... %s %d\n\n"
  "Pass is 60+ unless the challenge says otherwise.\n"
  "Results: Agent/result1.txt ... result4.txt\n",
  DojoSt(dojo_st[0]),dojo_sc[0],
  DojoSt(dojo_st[1]),dojo_sc[1],
  DojoSt(dojo_st[2]),dojo_sc[2],
  DojoSt(dojo_st[3]),dojo_sc[3]);
  PopUp(st,Fs,&pu);
  if (TaskValidate(pu)) Kill(pu);
  Free(st);
}
#endif
