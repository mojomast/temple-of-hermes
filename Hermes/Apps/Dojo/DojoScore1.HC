#ifndef DOJO_SCORE1_HC
#define DOJO_SCORE1_HC
#include "DojoScore.HC"
I64 DojoCheck1()
{
  I64 x,y,c,staff=0,sl=0,sr=0,wg=0,tot=0,s,sm;
  CDC *dc=DCNew(160,160);
  DCFill(dc,BLACK);
  U8 *p=DojoAgent("solution1.txt");
  DojoCmdDraw(p,dc); Free(p);
  for (y=0;y<160;y++)
    for (x=0;x<160;x++)
      if (c=DojoPix(dc,x,y))
      {
        tot++;
        if (x>=76 && x<=84) staff++;
        if (y>=40 && x<76) sl++;
        if (y>=40 && x>84) sr++;
        if (y<60) wg++;
      }
  s=DojoCap(staff,90,30);
  sm=DojoMin(sl,sr);
  s+=DojoCap(sm,120,30);
  s+=DojoCap(wg,260,20);
  s+=DojoCap(tot,500,20);
  Bool pass=s>=60 && staff>70 && sl>80 && sr>80;
  U8 *d=MStrPrint("staff=%d serpL=%d serpR=%d wings=%d px=%d",staff,sl,sr,wg,tot);
  DojoWriteResult(1,"caduceus",s,pass,d);
  Free(d); DCDel(dc);
  return s;
}
#endif
