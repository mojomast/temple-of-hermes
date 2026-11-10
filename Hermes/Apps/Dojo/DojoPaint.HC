#ifndef DOJO_PAINT_HC
#define DOJO_PAINT_HC
#include "DojoScreen.HC"
U0 DojoDrawIt(CTask *,CDC *dc)
{
  I64 i,y;
  DCFill(dc,BLACK);
  if (dojo_plate) GrBlot(dc,0,0,dojo_plate);
  else { dc->color=BLUE; GrRect(dc,0,0,640,64); dc->color=YELLOW; GrPrint(dc,200,20,"HERMES DOJO"); }
  dc->color=LTRED; GrPrint(dc,600,4,"NEW");
  DojoPanel(dc,16,80,208,296,"TEKNIUM / GAME TRAINER",LTBLUE);
  dc->color=BLACK;
  if (dojo_tek) GrBlot(dc,24,96,dojo_tek);
  dc->color=WHITE; GrPrint(dc,96,100,"TEKNIUM");
  dc->color=LTGRAY; GrPrint(dc,96,112,"game character");
  dc->color=LTCYAN; GrPrint(dc,96,124,"energy blade");
  DojoPanel(dc,24,168,192,64,"TRAINER VOICE",BROWN);
  dc->color=YELLOW; GrPrint(dc,32,186,"\"%s\"",DOJO_LINE);
  dc->color=LTGRAY; GrPrint(dc,32,202,"- game character");
  DojoCaduceus(dc,596,292,18);
  DojoPanel(dc,232,80,392,296,"SCORED CHALLENGES",LTGREEN);
  for (i=0;i<4;i++)
  {
    y=106+i*30;
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
  GrPrint(dc,248,338,"Pass 60+. Solutions live in Agent/.");
  DojoPanel(dc,16,384,608,80,"AGENT HOOK / CONTROLS",BROWN);
  dc->color=WHITE; GrPrint(dc,32,404,"1-4 run challenge   P plaque   R report   ESC exit");
  dc->color=LTCYAN; GrPrint(dc,32,420,"Agent: write Agent/solutionN.*, then");
  GrPrint(dc,32,436,"#include ChalN.HC; DojoChalN; read resultN.txt");
}
#endif
