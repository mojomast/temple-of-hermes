#ifndef DOJO_CLI_HC
#define DOJO_CLI_HC
#include "DojoCheck.HC"
U0 DojoCli(U8 *n)
{
  I64 i=Str2I64(n),s=DojoCheck(i);
  U8 *p=DojoAgent(""),*r=MStrPrint("%s/result%d.txt",p,i);
  "DOJO CLI %d score=%d result=%s\n",i,s,r;
  Free(r); Free(p);
}
#endif
