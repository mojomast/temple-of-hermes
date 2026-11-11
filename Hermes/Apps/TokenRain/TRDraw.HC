U0 TRStar(CDC *dc,CTask *task)
{
  I64 i,x,y,w=task->pix_width,h=task->pix_height;
  for (i=0;i<90;i++)
  {
    x=(i*97+17)%TR_W;
    y=TR_TOP+((i*61+29)%(TR_H-TR_TOP));
    if (x<w && y<h)
    {
      if (i%5)
        dc->color=DKGRAY;
      else
        dc->color=LTBLUE;
      GrPlot(dc,x,y);
    }
  }
}

U0 TRHeader(CDC *dc,CTask *task)
{
  if (tr_hdr)
    GrBlot(dc,0,0,tr_hdr);
  else
  {
    dc->color=BLUE;
    GrRect(dc,0,0,TR_W,40);
    dc->color=YELLOW;
    GrPrint(dc,8,12,"THE THRESHOLD");
  }
  dc->color=BLACK;
  GrRect(dc,0,40,task->pix_width,16);
  dc->color=YELLOW;
  GrPrint(dc,8,44,"TOKEN RAIN");
  dc->color=LTGRAY;
  GrPrint(dc,200,44,"ARETE CATCH // GLYPH DODGE");
}

U0 TRGirl(CDC *dc,I64 x,I64 y)
{
  dc->color=BLACK;
  GrRect(dc,x-32,y-32,64,64);
  dc->color=DKGRAY;
  GrBorder(dc,x-33,y-33,x+32,y+32);
  if (tr_gr)
    GrBlot(dc,x-32,y-32,tr_gr);
  else
  {
    dc->color=LTPURPLE;
    GrFillCircle(dc,x,y-10,0,18);
    dc->color=LTBLUE;
    GrRect(dc,x-12,y-2,24,30);
  }
}

U0 TRToken(CDC *dc,CToken *t)
{
  I64 x=t->x,y=t->y;
  if (t->kind==0)
  {
    if (t->vy>130)
      dc->color=LTCYAN;
    else
      dc->color=YELLOW;
    GrLine(dc,x,y-8,x+8,y);
    GrLine(dc,x+8,y,x,y+8);
    GrLine(dc,x,y+8,x-8,y);
    GrLine(dc,x-8,y,x,y-8);
    dc->color=BLACK;
    GrPrint(dc,x-4,y-4,"A");
  }
  else
  {
    dc->color=RED;
    GrCircle(dc,x,y,7,2);
    dc->color=LTRED;
    GrLine(dc,x-5,y-5,x+5,y+5);
    GrLine(dc,x-5,y+5,x+5,y-5);
  }
}

U0 TRGate(CDC *dc)
{
  dc->color=DKGRAY;
  GrRect(dc,70,300,12,160);
  GrRect(dc,558,300,12,160);
  GrRect(dc,70,300,500,8);
  dc->color=LTGRAY;
  GrPrint(dc,244,302,"T H E   T H R E S H O L D");
}
