U0 TRTitle(CDC *dc,CTask *task)
{
  I64 x=(task->pix_width-420)/2,blink=tS*2;
  TRStar(dc,task);
  if (tr_plate)
    GrBlot(dc,0,0,tr_plate);
  else
    TRHeader(dc,task);
  dc->color=BLACK;
  GrRect(dc,x-10,168,440,48);
  dc->color=YELLOW;
  GrPrint(dc,x,176,"T O K E N   R A I N");
  dc->color=LTCYAN;
  GrPrint(dc,x,192,"NOUS GIRL AT THE THRESHOLD");
  dc->color=LTGRAY;
  GrPrint(dc,x,208,"NEW: CATCH ARETE / DODGE CURSED GLYPHS");
  if (tr_icon32)
    GrBlot(dc,72,248,tr_icon32);
  dc->color=YELLOW;
  GrPrint(dc,120,248,"ARETE TOKEN      +10");
  dc->color=LTRED;
  GrPrint(dc,120,264,"CURSED GLYPH     -1 LIFE");
  dc->color=WHITE;
  GrPrint(dc,120,288,"LEFT / RIGHT   OR   A / D");
  dc->color=LTGRAY;
  GrPrint(dc,120,312,"ENTER START      ESC EXIT");
  dc->color=LTPURPLE;
  GrPrint(dc,120,336,"BEST %04d",tr_high);
  if (blink&1)
  {
    dc->color=LTCYAN;
    GrPrint(dc,120,368,"PRESS ENTER TO PLAY");
  }
  TRGirl(dc,480,280);
  dc->color=DKGRAY;
  GrPrint(dc,120,440,"FICTIONAL GAME CHARACTER / 16-COLOR");
}
