#ifndef DOJO_SCORE2_HC
#define DOJO_SCORE2_HC
#include "DojoScore.HC"
I64 DojoCheck2()
{
  I64 s=0;
  U8 *p=DojoAgent("solution2.DD");
  U8 *b=FileRead(p); Free(p);
  if (!b)
  {
    DojoWriteResult(2,"DolDoc form",0,FALSE,"missing Agent/solution2.DD");
    return 0;
  }
  if (StrFind("BT,",b)) s+=25;
  if (StrFind("TX,",b)) s+=25;
  if (StrFind("Name",b)) s+=15;
  if (StrFind("Rank",b)) s+=15;
  if (StrFind("SUBMIT",b)) s+=20;
  U8 *d=MStrPrint("bytes=%d tags=%d",StrLen(b),s);
  DojoWriteResult(2,"DolDoc form",s,s>=75,d);
  Free(d); Free(b);
  return s;
}
#endif
