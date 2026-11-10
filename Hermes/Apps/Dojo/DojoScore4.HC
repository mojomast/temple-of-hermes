#ifndef DOJO_SCORE4_HC
#define DOJO_SCORE4_HC
#include "DojoScore.HC"
I64 DojoCheck4()
{
  I64 len=0,s=0;
  U8 *p=DojoAgent("solution4.txt");
  U8 *b=FileRead(p); Free(p);
  if (b)
  {
    len=StrLen(b);
    if (StrFind("HERMES-DOJO-ECHO",b)) { if (len>=12) s=100; else s=60; }
    Free(b);
  }
  U8 *d=MStrPrint("bytes=%d token=%d",len,s>0);
  DojoWriteResult(4,"file echo",s,s>=60,d);
  Free(d);
  return s;
}
#endif
