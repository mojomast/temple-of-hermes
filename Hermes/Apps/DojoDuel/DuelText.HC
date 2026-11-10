#ifndef DUEL_TEXT_HC_V5
#define DUEL_TEXT_HC_V5
#include "DuelGlobals.HC"

U8 *DuelScorePath()
{
  return HermesStateFile("DojoDuel","DojoDuelScore.TXT");
}

U8 *DuelResultPath()
{
  return HermesStateFile("DojoDuel","DojoDuelResult.TXT");
}
U8 *duel_tokens[DUEL_NCH]={
 "U0","I64","MAlloc","Free","while","GrLine","Sleep","Fs->draw_it"};
U8 *duel_hints[DUEL_NCH]={
 "the void type","64-bit integer","heap allocate","release memory",
 "loop keyword","draw a line","yield the task","paint hook"};
U8 *duel_coach[DUEL_NCH]={
 "Ship first, patch later.","Small tokens cut deep.","Steady hands win.",
 "Type clean, strike true.","One line, one strike.","Breathe, then commit.",
 "Precision beats speed.","Finish the run."};
U8 *duel_agent_ans[DUEL_NCH]={
 "U0","I64","MAlloc","Free","while","GrLine","Sleep","Fs->draw_it"};
U8 *DuelMark(I64 v)
{
  if (v==1) return "PASS";
  if (v==0) return "FAIL";
  return "--";
}
U8 *DuelYn(Bool b)
{
  if (b) return "PASS";
  return "FAIL";
}
I64 DuelEq(U8 *a,U8 *b)
{
  I64 ca,cb;
  while (*a && *b)
  {
    ca=*a++; cb=*b++;
    if (ca>='A' && ca<='Z') ca+=32;
    if (cb>='A' && cb<='Z') cb+=32;
    if (ca!=cb) return FALSE;
  }
  return !*a && !*b;
}
U0 DuelFlash(U8 *s)
{
  I64 i=0;
  while (s[i] && i<63) { duel_flash[i]=s[i]; i++; }
  duel_flash[i]=0;
}
#endif
