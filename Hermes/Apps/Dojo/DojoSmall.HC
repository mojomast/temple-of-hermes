#ifndef DOJO_SMALL_HC
#define DOJO_SMALL_HC
#include "Dojo.HC"
U8 *DojoYN(Bool b)
{
  if (b) return "PASS";
  return "FAIL";
}
U8 *DojoSt(I64 s)
{
  if (s==1) return "PASS";
  if (s==0) return "FAIL";
  return "--";
}
I64 DojoMin(I64 a,I64 b)
{
  if (a<b) return a;
  return b;
}
I64 DojoCap(I64 v,I64 full,I64 max)
{
  if (v>=full) return max;
  return v*max/full;
}
#endif
