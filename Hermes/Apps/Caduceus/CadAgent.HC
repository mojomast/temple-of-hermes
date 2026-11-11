I64 CadScoreDir(I32 dx,I32 dy)
{
  I32 j,nx,ny,fx,fy;
  I64 d,t;
  if (dx==-cad_dx && dy==-cad_dy) return -1;
  nx=cad_sx[0]+dx;
  ny=cad_sy[0]+dy;
  if (nx<0 || nx>=CAD_COLS || ny<0 || ny>=CAD_ROWS) return -1;
  for (j=1;j<cad_len;j++)
    if (cad_sx[j]==nx && cad_sy[j]==ny)
      return -1;
  d=1000000;
  for (j=0;j<CAD_FOOD;j++)
    if (cad_food[j]) {
      fx=cad_fx[j];
      fy=cad_fy[j];
      t=nx-fx;
      if (t<0) t=-t;
      if (ny<fy) t+=fy-ny; else t+=ny-fy;
      if (t<d) d=t;
    }
  return d;
}

U0 CadAgentDir()
{
  I32 bx,by;
  I64 bd,d;
  bx=cad_dx;
  by=cad_dy;
  bd=0x7FFFFFFFFFFFFFFF;
  d=CadScoreDir(1,0);
  if (d>=0 && d<bd) { bd=d; bx=1; by=0; }
  d=CadScoreDir(0,1);
  if (d>=0 && d<bd) { bd=d; bx=0; by=1; }
  d=CadScoreDir(-1,0);
  if (d>=0 && d<bd) { bd=d; bx=-1; by=0; }
  d=CadScoreDir(0,-1);
  if (d>=0 && d<bd) { bd=d; bx=0; by=-1; }
  if (bd<0x7FFFFFFFFFFFFFFF) CadSetDir(bx,by);
}

U0 CaduceusAgent(U8 *out_file=NULL)
{
  I32 i;
  U8 *st,*res,*path;
  if (out_file && *out_file)
    path=StrNew(out_file);
  else
    path=CadResultPath();
  CadReset();
  CadStart();
  cad_sound=FALSE;
  for (i=0;i<900;i++) {
    if (!cad_alive) break;
    CadAgentDir();
    CadStep();
  }
  if (cad_alive) {
    cad_alive=FALSE;
    StrCpy(cad_msg,"Southpaw (NEW): The coil rests.");
  } else
    StrCpy(cad_msg,"Southpaw (NEW): The serpent sleeps.");
  CadSaveScore();
  if (cad_score>=30) res="PASS"; else res="FAIL";
  st=MStrPrint("score=%d\nlength=%d\nticks=%d\nresult=%s\n",
    cad_score,cad_len,cad_ticks,res);
  if (path && *path)
  {
    try
    {
      FileWrite(path,st,StrLen(st));
    }
    catch
      Fs->catch_except=TRUE;
  }
  Free(st);
  Free(path);
}
