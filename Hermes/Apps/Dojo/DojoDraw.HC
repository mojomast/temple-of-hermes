#ifndef DOJO_DRAW_HC
#define DOJO_DRAW_HC
#include "Dojo.HC"
U0 DojoFillRect(CDC *dc,I64 x,I64 y,I64 w,I64 h,I64 col)
{
  I64 i;
  dc->color=col;
  for (i=0;i<h;i++) GrLine(dc,x,y+i,x+w-1,y+i);
}
U0 DojoPanel(CDC *dc,I64 x,I64 y,I64 w,I64 h,U8 *title,I64 col)
{
  DojoFillRect(dc,x,y,w,h,BLACK);
  dc->color=col; GrRect(dc,x,y,w,h);
  dc->color=YELLOW; GrPrint(dc,x+8,y+6,"%s",title);
}
U0 DojoCaduceus(CDC *dc,I64 cx,I64 cy,I64 s)
{
  I64 i;
  dc->color=YELLOW;
  GrLine(dc,cx,cy-s,cx,cy+s);
  GrCircle(dc,cx,cy-s-4,3);
  dc->color=LTCYAN;
  for (i=0;i<s;i++)
  {
    GrPlot(dc,cx-8+AbsI64(i-s/2)/2,cy-i);
    GrPlot(dc,cx+8-AbsI64(i-s/2)/2,cy-i);
    GrPlot(dc,cx-8+AbsI64(i-s/2)/2,cy+i);
    GrPlot(dc,cx+8-AbsI64(i-s/2)/2,cy+i);
  }
  dc->color=WHITE;
  GrLine(dc,cx-18,cy-s+6,cx-4,cy-s+2);
  GrLine(dc,cx+18,cy-s+6,cx+4,cy-s+2);
}
#endif
