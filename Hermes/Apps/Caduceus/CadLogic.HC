U32 CadRand()
{
  cad_seed=cad_seed*1664525+1013904223;
  return cad_seed;
}

I64 CadLoadHi()
{
  I64 sz,v=0;
  U8 *st;
  if (FileFind(CAD_SCORE))
    st=FileRead(CAD_SCORE,&sz);
  else
    st=NULL;
  if (st) {
    v=Str2I64(st);
    Free(st);
  }
  return v;
}

U0 CadSaveScore()
{
  U8 *st;
  if (cad_score>cad_hi) cad_hi=cad_score;
  DirMk("C:/Tmp");
  st=MStrPrint("%d\n",cad_hi);
  FileWrite(CAD_SCORE,st,StrLen(st));
  Free(st);
}

Bool CadBody(I32 x,I32 y)
{
  I32 i;
  for (i=0;i<cad_len;i++)
    if (cad_sx[i]==x && cad_sy[i]==y)
      return TRUE;
  return FALSE;
}

Bool CadFree(I32 x,I32 y)
{
  I32 i;
  if (CadBody(x,y)) return FALSE;
  for (i=0;i<CAD_FOOD;i++)
    if (cad_food[i] && cad_fx[i]==x && cad_fy[i]==y)
      return FALSE;
  return TRUE;
}

U0 CadFoodNew(I32 i)
{
  I32 t,x,y;
  for (t=0;t<800;t++) {
    x=CadRand()%CAD_COLS;
    y=CadRand()%CAD_ROWS;
    if (CadFree(x,y)) {
      cad_fx[i]=x;
      cad_fy[i]=y;
      cad_food[i]=TRUE;
      return;
    }
  }
  cad_food[i]=FALSE;
}
