#ifndef DOJO_SCORE3_HC
#define DOJO_SCORE3_HC
#include "DojoScore.HC"
I64 DojoCheck3()
{
  I64 x,y,c,tot=0,q0=0,q1=0,q2=0,q3=0,ncol=0,vc=0,hc=0,s,qm;
  I64 col[16];
  MemSet(col,0,sizeof(col));
  CDC *dc=DCNew(32,32);
  DCFill(dc,BLACK);
  U8 *p=DojoAgent("solution3.txt");
  DojoCmdDraw(p,dc); Free(p);
  for (y=0;y<32;y++)
    for (x=0;x<32;x++)
      if (c=DojoPix(dc,x,y))
      {
        tot++; col[c]=1;
        if (x<16 && y<16) q0++;
        else if (x>=16 && y<16) q1++;
        else if (x<16 && y>=16) q2++;
        else q3++;
      }
  for (x=1;x<16;x++) if (col[x]) ncol++;
  for (y=0;y<32;y++) if (DojoPix(dc,16,y)) vc++;
  for (x=0;x<32;x++) if (DojoPix(dc,x,16)) hc++;
  s=DojoCap(tot,40,30);
  qm=DojoMin(q0,q1); qm=DojoMin(qm,q2); qm=DojoMin(qm,q3);
  s+=DojoCap(qm,5,30);
  if (ncol>=2 && ncol<=8) s+=20; else s+=10;
  if (vc>10 && hc>10) s+=20; else s+=10;
  Bool pass=s>=60 && tot>30 && qm>3;
  U8 *d=MStrPrint("px=%d quads=%d,%d,%d,%d colors=%d",tot,q0,q1,q2,q3,ncol);
  DojoWriteResult(3,"draw_it sprite",s,pass,d);
  Free(d); DCDel(dc);
  return s;
}
#endif
