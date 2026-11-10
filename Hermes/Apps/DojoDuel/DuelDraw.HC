#ifndef DUEL_DRAW_V6_HC
#define DUEL_DRAW_V6_HC
#include "DuelText.HC"
#include "DuelAssets.HC"
U0 DuelFill(CDC *dc,I64 x,I64 y,I64 w,I64 h,I64 col)
{
  I64 i;
  dc->color=col;
  for (i=0;i<h;i++) GrLine(dc,x,y+i,x+w-1,y+i);
}
U0 DuelPanel(CDC *dc,I64 x,I64 y,I64 w,I64 h,U8 *title,I64 col)
{
  DuelFill(dc,x,y,w,h,BLACK);
  dc->color=col; GrBorder(dc,x,y,x+w-1,y+h-1);
  if (title)
  {
    dc->color=YELLOW;
    GrPrint(dc,x+8,y+6,"%s",title);
  }
}
U0 DuelCenter(CDC *dc,I64 x,I64 w,I64 y,U8 *s,I64 col)
{
  I64 tw=StrLen(s)*8;
  if (tw>w) tw=w;
  dc->color=col;
  GrPrint(dc,x+(w-tw)/2,y,"%s",s);
}
U0 DuelTimer(CDC *dc,I64 x,I64 y,I64 w)
{
  F64 rem=duel_deadline-tS;
  I64 tenths,fill,col;
  if (rem<0) rem=0;
  if (rem>DUEL_TIME) rem=DUEL_TIME;
  tenths=ToI64(rem*10.0);
  fill=ToI64(rem*w/DUEL_TIME);
  DuelFill(dc,x,y,w,12,DKGRAY);
  col=GREEN;
  if (rem<DUEL_TIME/2) col=YELLOW;
  if (rem<DUEL_TIME/4) col=LTRED;
  if (fill>0) DuelFill(dc,x,y,fill,12,col);
  dc->color=WHITE;
  GrPrint(dc,x+w+8,y+2,"TIME %d.%d",tenths/10,tenths%10);
}
U0 DuelBanner(CDC *dc,U8 *s)
{
  DuelFill(dc,0,0,640,40,BLUE);
  dc->color=YELLOW;
  GrPrint(dc,16,14,"%s",s);
  dc->color=LTRED;
  GrPrint(dc,604,4,"NEW");
}
U0 DuelDrawTitle(CDC *dc)
{
  if (duel_plate) GrBlot(dc,0,0,duel_plate);
  else DuelBanner(dc,DUEL_NAME);
  DuelPanel(dc,16,56,608,400,"TIMED HOLYC TYPING DUEL",LTBLUE);
  if (duel_tek) GrBlot(dc,40,80,duel_tek);
  dc->color=WHITE;
  GrPrint(dc,128,84,"DOJO DUEL");
  dc->color=LTCYAN;
  GrPrint(dc,128,104,"a timed HolyC typing duel");
  dc->color=YELLOW;
  GrPrint(dc,128,128,"BEST %d   RUNS %d",duel_best,duel_runs);
  dc->color=LTGRAY;
  GrPrint(dc,128,156,"Type the HolyC token before the timer dies.");
  DuelCenter(dc,16,608,340,"PRESS ENTER TO DUEL",LTGREEN);
  dc->color=WHITE;
  GrPrint(dc,40,364,"ENTER start   ESC shell   P wall plaque");
  GrPrint(dc,40,380,"Each strike adds time bonus and streak.");
  dc->color=LTCYAN;
  {
    U8 *rp=DuelResultPath();
    GrPrint(dc,40,404,"Agent: DojoDuel(TRUE) writes %s",rp);
    Free(rp);
  }
  dc->color=LTGRAY;
  GrPrint(dc,40,424,"https://nousresearch.com/");
  GrPrint(dc,40,436,"nouscoder-14b-a-competitive-olympiad-programming-model");
  dc->color=LTRED;
  GrPrint(dc,600,62,"NEW");
}
U0 DuelDrawPlay(CDC *dc)
{
  U8 show[64];
  I64 i,n,start,tw;
  if (duel_bar) GrBlot(dc,0,0,duel_bar);
  else DuelBanner(dc,DUEL_NAME);
  dc->color=LTRED;
  GrPrint(dc,588,4,"NEW");
  DuelPanel(dc,12,48,224,416,"TEKNIUM / TRAINER",LTBLUE);
  if (duel_tek) GrBlot(dc,28,76,duel_tek);
  dc->color=WHITE;
  GrPrint(dc,100,80,"TEKNIUM");
  dc->color=LTGRAY;
  GrPrint(dc,100,96,"Nous universe");
  GrPrint(dc,100,110,"energy blade");
  dc->color=LTCYAN;
  GrPrint(dc,100,124,"duel coach");
  dc->color=BROWN;
  GrLine(dc,24,150,212,150);
  dc->color=YELLOW;
  GrPrint(dc,24,160,"TRAINER VOICE");
  dc->color=LTRED;
  GrPrint(dc,168,160,"NEW");
  dc->color=WHITE;
  GrPrint(dc,24,178,"%s",duel_coach[duel_idx%DUEL_NCH]);
  dc->color=LTGRAY;
  GrPrint(dc,24,400,"P plaque");
  GrPrint(dc,24,414,"ESC shell");
  GrPrint(dc,24,428,"ENTER submit");
  GrPrint(dc,24,446,"BEST %d",duel_best);
  DuelPanel(dc,248,48,380,416,"TIMED TYPING DUEL",LTGREEN);
  dc->color=WHITE;
  GrPrint(dc,264,64,"CHALLENGE %d / %d",duel_idx+1,DUEL_NCH);
  dc->color=LTGRAY;
  GrPrint(dc,264,80,"%s",duel_hints[duel_idx]);
  DuelFill(dc,264,96,348,56,BLACK);
  dc->color=LTCYAN; GrBorder(dc,264,96,611,151);
  tw=StrLen(duel_tokens[duel_idx])*8;
  dc->color=YELLOW;
  GrPrint(dc,264+(348-tw)/2,120,"%s",duel_tokens[duel_idx]);
  dc->color=LTGRAY;
  GrPrint(dc,264,158,"YOUR INPUT");
  DuelFill(dc,264,168,348,40,BLACK);
  dc->color=WHITE; GrBorder(dc,264,168,611,207);
  n=StrLen(duel_buf); start=0;
  if (n>38) start=n-38;
  for (i=0;i<n-start;i++) show[i]=duel_buf[start+i];
  show[i]='_'; show[i+1]=0;
  dc->color=WHITE;
  GrPrint(dc,272,184,"%s",show);
  DuelTimer(dc,264,224,280);
  dc->color=YELLOW;
  GrPrint(dc,264,252,"SCORE %d",duel_score);
  dc->color=LTCYAN;
  GrPrint(dc,480,252,"STREAK %d",duel_streak);
  if (duel_lastok==1)
  {
    dc->color=LTGREEN;
    GrPrint(dc,264,274,"CLEAN STRIKE +%d",duel_lastgain);
  }
  else if (duel_lastok==0)
  {
    dc->color=LTRED;
    if (duel_lasttime) GrPrint(dc,264,274,"TIME - STREAK RESET");
    else GrPrint(dc,264,274,"MISS - STREAK RESET");
  }
  else
  {
    dc->color=LTGRAY;
    GrPrint(dc,264,274,"%s",duel_flash);
  }
  dc->color=BROWN;
  GrLine(dc,264,296,612,296);
  dc->color=YELLOW;
  GrPrint(dc,264,304,"NEW COACH LINE");
  dc->color=WHITE;
  GrPrint(dc,264,318,"%s",duel_coach[duel_idx%DUEL_NCH]);
  dc->color=LTCYAN;
  GrPrint(dc,264,344,"AGENT HOOK");
  dc->color=LTGRAY;
  GrPrint(dc,264,360,"DojoDuel(TRUE) writes");
  {
    U8 *rp=DuelResultPath();
    GrPrint(dc,264,372,"%s",rp);
    Free(rp);
  }
  dc->color=YELLOW;
  GrPrint(dc,264,396,"BEST %d  RUNS %d",duel_best,duel_runs);
  dc->color=LTGRAY;
  GrPrint(dc,264,416,"PLAQUE: P   nousresearch.com");
  GrPrint(dc,264,440,"ENTER submit  BKSP fix  ESC exit");
}
U0 DuelDrawDone(CDC *dc)
{
  I64 i,x,y;
  if (duel_plate) GrBlot(dc,0,0,duel_plate);
  else DuelBanner(dc,DUEL_NAME);
  DuelPanel(dc,16,56,608,400,"DUEL COMPLETE",LTGREEN);
  dc->color=WHITE;
  GrPrint(dc,40,76,"DUEL COMPLETE");
  dc->color=YELLOW;
  GrPrint(dc,40,104,"SCORE %d",duel_score);
  dc->color=LTCYAN;
  GrPrint(dc,200,104,"BEST %d",duel_best);
  GrPrint(dc,360,104,"BEST STREAK %d",duel_beststreak);
  dc->color=BROWN;
  GrLine(dc,40,124,600,124);
  for (i=0;i<DUEL_NCH;i++)
  {
    x=40; y=138+(i%4)*16;
    if (i>=4) x=320;
    dc->color=WHITE;
    GrPrint(dc,x,y,"%d %s",i+1,duel_tokens[i]);
    if (duel_pass[i]==1) dc->color=LTGREEN;
    else if (duel_pass[i]==0) dc->color=LTRED;
    else dc->color=LTGRAY;
    GrPrint(dc,x+120,y,"%s",DuelMark(duel_pass[i]));
  }
  dc->color=LTGREEN;
  GrPrint(dc,40,220,"ENTER = duel again     ESC = shell");
  dc->color=LTCYAN;
  {
    U8 *rp=DuelResultPath();
    GrPrint(dc,40,240,"Agent result: %s",rp);
    Free(rp);
  }
  dc->color=LTGRAY;
  GrPrint(dc,40,272,"https://nousresearch.com/");
  GrPrint(dc,40,284,"nouscoder-14b-a-competitive-olympiad-programming-model");
  dc->color=LTRED;
  GrPrint(dc,40,308,"NEW");
  dc->color=WHITE;
  GrPrint(dc,72,308,"%s",duel_coach[duel_idx%DUEL_NCH]);
}
U0 DuelDrawIt(CTask *,CDC *dc)
{
  DCFill(dc,BLACK);
  if (duel_state==DUEL_PLAY) DuelDrawPlay(dc);
  else if (duel_state==DUEL_DONE) DuelDrawDone(dc);
  else DuelDrawTitle(dc);
}
#endif
