U0 TRPlayView(CDC *dc,CTask *task)
{
  I64 i,px;
  TRStar(dc,task);
  TRGate(dc);
  for (i=0;i<TR_MAX;i++)
    if (tr_tok[i].on)
      TRToken(dc,&tr_tok[i]);
  px=tr_px;
  TRGirl(dc,px,TR_PY+32);
  TRHeader(dc,task);
  dc->color=BLACK;
  GrRect(dc,0,40,task->pix_width,14);
  dc->color=YELLOW;
  GrPrint(dc,8,42,"SCORE %04d",tr_score);
  if (tr_icon16)
    GrBlot(dc,160,40,tr_icon16);
  dc->color=LTCYAN;
  GrPrint(dc,180,42,"LIVES %d",tr_lives);
  dc->color=LTPURPLE;
  GrPrint(dc,300,42,"BEST %04d",tr_high);
  dc->color=LTGRAY;
  GrPrint(dc,430,42,"ARETE %d",tr_catches);
  if (tr_flash>0)
  {
    dc->color=LTRED;
    GrBorder(dc,2,2,task->pix_width-3,task->pix_height-3);
  }
  if (tr_state==2)
  {
    dc->color=BLACK;
    GrRect(dc,150,180,340,132);
    dc->color=RED;
    GrBorder(dc,150,180,490,312);
    dc->color=YELLOW;
    GrPrint(dc,210,200,"RUN COMPLETE");
    dc->color=WHITE;
    GrPrint(dc,210,228,"SCORE %04d",tr_score);
    dc->color=LTCYAN;
    GrPrint(dc,210,248,"BEST  %04d",tr_high);
    dc->color=LTGRAY;
    GrPrint(dc,210,276,"ENTER AGAIN   ESC TITLE");
  }
}
