U0 CadBars(CDC *dc)
{
  dc->color=BLACK;
  GrRect(dc,0,0,640,44);
  GrRect(dc,0,416,640,64);
  if (cad_logo) GrBlot(dc,6,6,cad_logo);
  if (cad_sp) GrBlot(dc,602,6,cad_sp);
  dc->color=LTCYAN;
  GrPrint(dc,46,10,"CADUCEUS - TEMPLE SERPENT");
  dc->color=WHITE;
  GrPrint(dc,46,26,"Score:%d  Best:%d  Len:%d",
    cad_score,cad_hi,cad_len);
}

U0 CadOverlay(CDC *dc)
{
  if (cad_state==CAD_TITLE) {
    dc->color=BLACK;
    GrRect(dc,166,178,308,112);
    dc->color=LTCYAN;
    GrBorder(dc,166,178,474,290);
    GrPrint(dc,196,192,"CADUCEUS");
    dc->color=YELLOW;
    GrPrint(dc,196,210,"Guide the temple serpent.");
    dc->color=WHITE;
    GrPrint(dc,196,226,"Eat offerings. Avoid walls.");
    GrPrint(dc,196,242,"Avoid your own tail.");
    dc->color=LTGREEN;
    GrPrint(dc,196,262,"SPACE or ARROW to begin");
  }
  if (cad_state==CAD_OVER) {
    dc->color=BLACK;
    GrRect(dc,176,176,288,108);
    dc->color=RED;
    GrBorder(dc,176,176,464,284);
    GrPrint(dc,212,190,"GAME OVER");
    dc->color=YELLOW;
    GrPrint(dc,212,210,"Score:%d  Length:%d",cad_score,cad_len);
    dc->color=WHITE;
    GrPrint(dc,212,230,"ENTER - play again");
    GrPrint(dc,212,248,"ESC - leave the temple");
  }
}

U0 CadFooter(CDC *dc)
{
  dc->color=WHITE;
  GrPrint(dc,8,424,"%s",cad_msg);
  dc->color=LTGRAY;
  GrPrint(dc,8,442,"Arrows/WASD steer. P toggles auto-play.");
  GrPrint(dc,8,458,"NEW mode: Southpaw watches the coil.");
}
