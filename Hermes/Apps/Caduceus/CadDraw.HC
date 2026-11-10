U0 CadCell(CDC *dc,I32 cx,I32 cy,I32 color,I32 pad)
{
  dc->color=color;
  GrRect(dc,CAD_X+cx*CAD_CELL+pad,CAD_Y+cy*CAD_CELL+pad,
    CAD_CELL-2*pad,CAD_CELL-2*pad);
}

U0 CadBoard(CDC *dc)
{
  I32 i;
  dc->color=BLACK;
  GrRect(dc,CAD_X,CAD_Y,CAD_COLS*CAD_CELL,CAD_ROWS*CAD_CELL);
  dc->color=DKGRAY;
  GrBorder(dc,CAD_X-1,CAD_Y-1,CAD_X+CAD_COLS*CAD_CELL,
    CAD_Y+CAD_ROWS*CAD_CELL);
  for (i=4;i<CAD_COLS;i+=4) {
    GrPlot(dc,CAD_X+i*CAD_CELL,CAD_Y);
    GrPlot(dc,CAD_X+i*CAD_CELL,CAD_Y+CAD_ROWS*CAD_CELL-1);
  }
  for (i=4;i<CAD_ROWS;i+=4) {
    GrPlot(dc,CAD_X,CAD_Y+i*CAD_CELL);
    GrPlot(dc,CAD_X+CAD_COLS*CAD_CELL-1,CAD_Y+i*CAD_CELL);
  }
}

U0 CadSnake(CDC *dc)
{
  I32 i;
  for (i=cad_len-1;i>=0;i--) {
    if (i==0)
      CadCell(dc,cad_sx[i],cad_sy[i],LTCYAN,1);
    else if (i&1)
      CadCell(dc,cad_sx[i],cad_sy[i],GREEN,2);
    else
      CadCell(dc,cad_sx[i],cad_sy[i],LTGREEN,2);
  }
}

U0 CadFoods(CDC *dc)
{
  I32 i;
  for (i=0;i<CAD_FOOD;i++)
    if (cad_food[i]) {
      dc->color=YELLOW;
      GrRect(dc,CAD_X+cad_fx[i]*CAD_CELL+4,
        CAD_Y+cad_fy[i]*CAD_CELL+4,8,8);
    }
}
