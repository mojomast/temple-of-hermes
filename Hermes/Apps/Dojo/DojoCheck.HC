#ifndef DOJO_CHECK_HC
#define DOJO_CHECK_HC
#include "DojoScore1.HC"
#include "DojoScore2.HC"
#include "DojoScore3.HC"
#include "DojoScore4.HC"
I64 DojoCheck(I64 n)
{
  if (n==1) return DojoCheck1();
  if (n==2) return DojoCheck2();
  if (n==3) return DojoCheck3();
  if (n==4) return DojoCheck4();
  return -1;
}
#endif
