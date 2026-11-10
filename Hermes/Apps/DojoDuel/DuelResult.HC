#ifndef DUEL_RESULT_HC_V5
#define DUEL_RESULT_HC_V5
#include "DuelText.HC"
U0 DuelAppend(U8 **pb,U8 *add)
{
  U8 *old=*pb;
  *pb=MStrPrint("%s%s",old,add);
  Free(old);
}
U0 DuelWriteAgentResult(U8 *out_file=NULL)
{
  I64 i,ok,nok=0,sc=0;
  U8 *b=StrNew("DOJO DUEL AGENT RESULT\n"),*line,*path;
  for (i=0;i<DUEL_NCH;i++)
  {
    ok=DuelEq(duel_agent_ans[i],duel_tokens[i]);
    if (ok) { nok++; sc+=100; }
    line=MStrPrint("%d %s: %s\n",i+1,duel_tokens[i],DuelYn(ok));
    DuelAppend(&b,line);
    "AGENT %d %s %s\n",i+1,duel_tokens[i],DuelYn(ok);
    Free(line);
  }
  line=MStrPrint("TOTAL: %d/%d\nSCORE: %d\nRESULT: %s\n",
    nok,DUEL_NCH,sc,DuelYn(nok==DUEL_NCH));
  DuelAppend(&b,line);
  Free(line);
  if (out_file && *out_file) path=StrNew(out_file);
  else path=StrNew("C:/Tmp/DojoDuelResult.TXT");
  if (!FileFind("C:/Tmp")) DirMk("C:/Tmp");
  FileWrite(path,b,StrLen(b));
  "DOJO DUEL AGENT: %d/%d score %d -> %s\n",nok,DUEL_NCH,sc,path;
  Free(path);
  Free(b);
}
U0 DuelPlaque()
{
  CTask *pu=NULL;
  U8 *st=
  "$$WW,1$$$$YELLOW$$DOJO DUEL WALL PLAQUE$$FG$$\n\n"
  "Teknium appears only as Kyle's character from the Nous universe.\n"
  "Trainer voice from the game is marked NEW.\n\n"
  "NousCoder-14B:\n"
  "$$TX,\"https://nousresearch.com/nouscoder-14b-a-competitive-olympiad-programming-model\",HTML=\"https://nousresearch.com/nouscoder-14b-a-competitive-olympiad-programming-model\"$$\n\n"
  "HolyC best practices: docs/HOLYC-BEST-PRACTICES.md\n"
  "High score: C:/Tmp/DojoDuelScore.TXT\n"
  "Agent result: C:/Tmp/DojoDuelResult.TXT\n";
  PopUp(st,Fs,&pu);
  if (TaskValidate(pu)) Kill(pu);
}
#endif
