#ifndef DOJO_CMD_HC
#define DOJO_CMD_HC
#include "Dojo.HC"
I64 DojoClamp(I64 v,I64 lo,I64 hi)
{
  if (v<lo) return lo;
  if (v>hi) return hi;
  return v;
}
U0 DojoCmdDraw(U8 *file,CDC *dc)
{
  I64 sz,x1,y1,x2,y2,c;
  U8 *buf=FileRead(file,&sz),*p,*nl,*nx,*q;
  if (!buf) return;
  p=buf;
  while (*p)
  {
    while (*p==' '||*p=='\t') p++;
    nl=p;
    while (*nl && *nl!='\n') nl++;
    if (*nl) nx=nl+1; else nx=nl;
    *nl=0;
    if (*p && *p!='#')
    {
      if (!StrNCmp(p,"COLOR",5))
      {
        q=p+5; c=Str2I64(q,,&q); dc->color=c&15;
      }
      else if (!StrNCmp(p,"LINE",4))
      {
        q=p+4; x1=Str2I64(q,,&q); y1=Str2I64(q,,&q);
        x2=Str2I64(q,,&q); y2=Str2I64(q,,&q);
        GrLine(dc,DojoClamp(x1,0,dc->width-1),DojoClamp(y1,0,dc->height-1),
                  DojoClamp(x2,0,dc->width-1),DojoClamp(y2,0,dc->height-1));
      }
      else if (!StrNCmp(p,"PLOT",4))
      {
        q=p+4; x1=Str2I64(q,,&q); y1=Str2I64(q,,&q);
        GrPlot(dc,DojoClamp(x1,0,dc->width-1),DojoClamp(y1,0,dc->height-1));
      }
      else if (!StrNCmp(p,"RECT",4))
      {
        q=p+4; x1=Str2I64(q,,&q); y1=Str2I64(q,,&q);
        x2=Str2I64(q,,&q); y2=Str2I64(q,,&q);
        GrRect(dc,DojoClamp(x1,0,dc->width-1),DojoClamp(y1,0,dc->height-1),x2,y2);
      }
      else if (!StrNCmp(p,"CIRCLE",6))
      {
        q=p+6; x1=Str2I64(q,,&q); y1=Str2I64(q,,&q); x2=Str2I64(q,,&q);
        GrCircle(dc,DojoClamp(x1,0,dc->width-1),DojoClamp(y1,0,dc->height-1),x2);
      }
    }
    p=nx;
  }
  Free(buf);
}
#endif
