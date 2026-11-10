U0 CadReset()
{
  I32 i;
  cad_len=3;
  cad_dx=1; cad_dy=0; cad_ndx=1; cad_ndy=0;
  cad_sx[0]=CAD_COLS/2; cad_sy[0]=CAD_ROWS/2;
  cad_sx[1]=cad_sx[0]-1; cad_sy[1]=cad_sy[0];
  cad_sx[2]=cad_sx[0]-2; cad_sy[2]=cad_sy[0];
  cad_score=0; cad_ticks=0; cad_delay=170;
  cad_alive=FALSE; cad_state=CAD_TITLE;
  cad_seed=0x5EED1234;
  for (i=0;i<CAD_FOOD;i++) cad_food[i]=FALSE;
  for (i=0;i<CAD_FOOD;i++) CadFoodNew(i);
  cad_hi=CadLoadHi();
  cad_auto=FALSE;
  StrCpy(cad_msg,"Southpaw: Run it locally!");
}

U0 CadStart()
{
  cad_state=CAD_PLAY;
  cad_alive=TRUE;
  cad_ticks=0;
  StrCpy(cad_msg,"Southpaw: Run it locally!");
}

U0 CadSetDir(I32 dx,I32 dy)
{
  if (dx==-cad_dx && dy==-cad_dy) return;
  if (dx==-cad_ndx && dy==-cad_ndy) return;
  cad_ndx=dx; cad_ndy=dy;
}
