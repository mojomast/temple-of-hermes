Bool CadDoKey(I64 ch,I64 scan)
{
  if (ch==CH_ESC || ch==CH_SHIFT_ESC) return TRUE;
  if (ch=='\n') {
    CadReset();
    CadStart();
    return FALSE;
  }
  if (cad_state==CAD_TITLE) {
    if (ch!=0 || scan==SC_CURSOR_UP || scan==SC_CURSOR_DOWN ||
        scan==SC_CURSOR_LEFT || scan==SC_CURSOR_RIGHT) {
      CadStart();
      return FALSE;
    }
  }
  if (cad_state==CAD_OVER) return FALSE;
  if (ch=='p' || ch=='P') {
    cad_auto=!cad_auto;
    return FALSE;
  }
  if (ch=='w' || ch=='W') CadSetDir(0,-1);
  else if (ch=='s' || ch=='S') CadSetDir(0,1);
  else if (ch=='a' || ch=='A') CadSetDir(-1,0);
  else if (ch=='d' || ch=='D') CadSetDir(1,0);
  else if (scan==SC_CURSOR_UP) CadSetDir(0,-1);
  else if (scan==SC_CURSOR_DOWN) CadSetDir(0,1);
  else if (scan==SC_CURSOR_LEFT) CadSetDir(-1,0);
  else if (scan==SC_CURSOR_RIGHT) CadSetDir(1,0);
  else if (ch==' ') {
    if (cad_state==CAD_TITLE) CadStart();
  }
  return FALSE;
}
