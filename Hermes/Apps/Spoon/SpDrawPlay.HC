#ifndef SP_DRAW_PLAY_HC
#define SP_DRAW_PLAY_HC

U0 SpDrawToken(CDC *dc,I64 x,I64 y,I64 kind)
{
  U8 c,ch;
  if (kind==SP_KIND_WALL)
  {
    c=LTBLUE;
    ch='W';
  }
  else if (kind==SP_KIND_SNIP)
  {
    c=LTGREEN;
    ch='S';
  }
  else if (kind==SP_KIND_PAL)
  {
    c=YELLOW;
    ch='P';
  }
  else
  {
    c=LTRED;
    ch='N';
  }
  dc->color=BLACK;
  GrRect(dc,x-9,y-9,18,18);
  dc->color=c;
  GrRect(dc,x-8,y-8,16,16);
  dc->color=WHITE;
  GrLine(dc,x-8,y-8,x+7,y-8);
  GrLine(dc,x-8,y-8,x-8,y+7);
  dc->color=DKGRAY;
  GrLine(dc,x+7,y-7,x+7,y+7);
  GrLine(dc,x-7,y+7,x+7,y+7);
  dc->color=BLACK;
  GrPrint(dc,x-3,y-4,"%c",ch);
}

U0 SpDrawSpoon(CDC *dc,F64 sx)
{
  I64 cx=ToI64(sx),y=SP_SPOON_Y;
  dc->color=LTGRAY;
  GrRect(dc,cx+34,y+1,38,6);
  GrRect(dc,cx+68,y-2,8,12);
  dc->color=LTCYAN;
  GrRect(dc,cx+34,y+2,34,3);
  dc->color=LTGRAY;
  GrEllipse(dc,cx,y,44,13);
  dc->color=LTCYAN;
  GrEllipse(dc,cx,y,40,10);
  dc->color=BLUE;
  GrEllipse(dc,cx,y,35,8);
  dc->color=LTCYAN;
  GrEllipse(dc,cx,y,30,5);
  dc->color=WHITE;
  GrLine(dc,cx-26,y-4,cx+18,y-4);
}

#endif
