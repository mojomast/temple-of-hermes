#ifndef SP_DRAW_OVER_HC
#define SP_DRAW_OVER_HC

U0 SpDrawTitle(CDC *dc)
{
  dc->color=BLACK;
  GrRect(dc,112,190,416,132);
  dc->color=YELLOW;
  GrBorder(dc,112,190,528,322,1,0);
  dc->color=LTRED;
  GrPrint(dc,276,204,"SPOON RALLY");
  dc->color=RED;
  GrRect(dc,356,204,36,12);
  dc->color=YELLOW;
  GrPrint(dc,361,206,"NEW");
  dc->color=WHITE;
  GrPrint(dc,204,226,"Hello I Hermes biggest fanboi");
  dc->color=LTCYAN;
  GrPrint(dc,276,240,"For Hermes!");
  dc->color=LTGRAY;
  GrPrint(dc,204,262,"Catch Don Piedro's offerings.");
  dc->color=WHITE;
  GrPrint(dc,196,278,"Left/Right move.  Enter starts.");
  dc->color=LTGRAY;
  GrPrint(dc,180,294,"Spoons are pretend. No real money.");
  dc->color=YELLOW;
  GrPrint(dc,236,306,"NEW flavor: Spoon Rally");
}

U0 SpDrawOver(CDC *dc,CSpoon *s)
{
  dc->color=BLACK;
  GrRect(dc,128,216,384,120);
  dc->color=LTRED;
  GrBorder(dc,128,216,512,336,1,0);
  dc->color=LTRED;
  GrPrint(dc,280,228,"ROUND OVER");
  dc->color=WHITE;
  GrPrint(dc,232,250,"Caught %d   Missed %d",s->caught,s->missed);
  dc->color=YELLOW;
  GrPrint(dc,248,266,"Score %d   High %d",s->score,s->high);
  dc->color=LTGRAY;
  GrPrint(dc,212,288,"Enter: run again   Esc: quit");
  dc->color=LTCYAN;
  GrPrint(dc,276,304,"For Hermes!");
}

#endif
