#ifndef SP_DRAW_TOP_HC
#define SP_DRAW_TOP_HC

U0 SpDrawBanner(CTask *task,CDC *dc,CSpoon *s)
{
  if (s->plate)
    GrBlot(dc,0,0,s->plate);
  else
  {
    dc->color=PURPLE;
    GrRect(dc,0,0,task->pix_width,160);
    dc->color=YELLOW;
    GrPrint(dc,16,24,"SPOON RALLY");
  }
  dc->color=BLACK;
  GrRect(dc,8,8,352,50);
  dc->color=YELLOW;
  GrBorder(dc,8,8,360,58,1,0);
  dc->color=YELLOW;
  GrPrint(dc,16,12,"SPOON RALLY");
  dc->color=RED;
  GrRect(dc,300,10,40,12);
  dc->color=YELLOW;
  GrPrint(dc,306,12,"NEW");
  dc->color=WHITE;
  GrPrint(dc,16,26,"Hello I Hermes biggest fanboi");
  dc->color=LTCYAN;
  GrPrint(dc,16,40,"For Hermes!  Spoons only, no real money.");
}

U0 SpDrawHud(CTask *task,CDC *dc,CSpoon *s)
{
  dc->color=BLACK;
  GrRect(dc,0,160,task->pix_width,20);
  dc->color=DKGRAY;
  GrLine(dc,0,179,task->pix_width-1,179);
  dc->color=LTGRAY;
  GrPrint(dc,8,166,"CAUGHT %d  MISSED %d  SCORE %d  HIGH %d",s->caught,s->missed,s->score,s->high);
  dc->color=YELLOW;
  GrPrint(dc,488,166,"TOSS %d/%d",s->tosses,SP_TOSSES);
}

#endif
