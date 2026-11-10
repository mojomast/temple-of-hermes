U0 CadDrawIt(CTask *task,CDC *dc)
{
  no_warn task;
  if (cad_wall) GrBlot(dc,0,0,cad_wall);
  CadBars(dc);
  if (cad_state==CAD_TITLE) {
    CadOverlay(dc);
    CadFooter(dc);
    return;
  }
  CadBoard(dc);
  CadFoods(dc);
  CadSnake(dc);
  CadOverlay(dc);
  CadFooter(dc);
}
