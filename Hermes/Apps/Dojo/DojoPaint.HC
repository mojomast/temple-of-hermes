#ifndef DOJO_PAINT_HC
#define DOJO_PAINT_HC
#include "DojoScreen.HC"
U0 DojoDrawIt(CTask *,CDC *dc)
{
  I64 i,y;
  DCFill(dc,BLACK);
  if (dojo_plate) GrBlot(dc,0,0,dojo_plate);
  else { dc->color=BLUE; GrRect(dc,0,0,640,160); dc->color=YELLOW; GrPrint(dc,200,70,"HERMES DOJO"); }
  dc->color=LTRED; GrPrint(dc,600,8,"NEW");
  DojoPanel(dc,16,168,208,224,"TEKNIUM / GAME TRAINER",LTBLUE);
  dc->color=BLACK;
  if (dojo_tek) GrBlot(dc,24,184,dojo_tek);
  dc->color=WHITE; GrPrint(dc,96,188,"TEKNIUM");
  dc->color=LTGRAY; GrPrint(dc,96,200,"Nous universe");
  dc->color=LTCYAN; GrPrint(dc,96,212,"energy blade");
  DojoPanel(dc,24,264,192,72,"TRAINER VOICE",BROWN);
  dc->color=YELLOW; GrPrint(dc,32,282,"\"%s\"",DOJO_LINE);
  dc->color=LTGRAY; GrPrint(dc,32,298,"- Nous universe");
  DojoCaduceus(dc,596,356,18);
  DojoPanel(dc,232,168,392,224,"SCORED CHALLENGES",LTGREEN);
  for (i=0;i<4;i++)
  {
    y=196+i*30;
    dc->color=WHITE; GrPrint(dc,248,y,"%s",dojo_names[i]);
    if (dojo_st[i]<0)
    {
      dc->color=LTGRAY; GrPrint(dc,520,y,"--");
    }
    else
    {
      if (dojo_st[i]) dc->color=BLACK; else dc->color=LTRED;
      GrPrint(dc,504,y,"%s %d",DojoSt(dojo_st[i]),dojo_sc[i]);
    }
  }
  dc->color=LTGRAY;
  GrPrint(dc,248,360,"Pass 60+. Solutions live in Agent/.");
  DojoPanel(dc,16,400,608,64,"AGENT HOOK / CONTROLS",BROWN);
  dc->color=WHITE; GrPrint(dc,32,414,"1-4 run challenge   P plaque   R report   ESC exit");
  dc->color=LTCYAN; GrPrint(dc,32,432,"Agent: write Agent/solutionN.*, then");
  GrPrint(dc,32,446,"#include ChalN.HC; DojoChalN; read resultN.txt");
}
#endif
