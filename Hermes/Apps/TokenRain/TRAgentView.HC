U0 TRAgentView(CDC *dc,CTask *task)
{
  I64 x=(task->pix_width-360)/2;
  TRStar(dc,task);
  TRGate(dc);
  TRHeader(dc,task);
  dc->color=BLACK;
  GrRect(dc,x-10,72,380,200);
  dc->color=LTCYAN;
  GrBorder(dc,x-10,72,x+370,272);
  dc->color=LTCYAN;
  GrPrint(dc,x,88,"AGENT RUN COMPLETE");
  dc->color=YELLOW;
  GrPrint(dc,x,116,"SCORE   %04d",tr_score);
  dc->color=WHITE;
  GrPrint(dc,x,136,"CATCHES %04d",tr_catches);
  dc->color=LTRED;
  GrPrint(dc,x,156,"HITS    %04d",tr_hits);
  dc->color=LTGREEN;
  GrPrint(dc,x,176,"FRAMES  %04d",tr_frames);
  dc->color=LTPURPLE;
  GrPrint(dc,x,204,"RESULT C:/Tmp/TokenRainResult.TXT");
  dc->color=LTGRAY;
  GrPrint(dc,x,240,"ENTER / ESC EXIT");
}

U0 TRDraw(CTask *task,CDC *dc)
{
  dc->color=BLACK;
  GrRect(dc,0,0,task->pix_width,task->pix_height);
  if (tr_state==0)
    TRTitle(dc,task);
  else if (tr_state==1 || tr_state==2)
    TRPlayView(dc,task);
  else
    TRAgentView(dc,task);
}
