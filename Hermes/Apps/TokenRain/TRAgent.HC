U0 TRAgentInput(I64 *l,I64 *r)
{
  I64 i,best=-1,avoid=0;
  F64 bx=320.0,bd=99999.0,ax=320.0,ad=99999.0,d;
  CToken *t;
  *l=*r=FALSE;
  for (i=0;i<TR_MAX;i++)
  {
    t=&tr_tok[i];
    if (t->on)
    {
      if (t->kind==0 && t->y<TR_PY)
      {
        d=t->x-tr_px;
        if (d<0)
          d=-d;
        d+=(TR_PY-t->y)*0.35;
        if (d<bd)
        {
          bd=d;
          bx=t->x;
          best=i;
        }
      }
      else if (t->kind==1 && t->y>TR_PY-170)
      {
        d=t->x-tr_px;
        if (d<0)
          d=-d;
        if (d<ad)
        {
          ad=d;
          ax=t->x;
          avoid=1;
        }
      }
    }
  }
  if (avoid && ad<54)
  {
    if (ax<tr_px)
      *r=TRUE;
    else
      *l=TRUE;
  }
  else if (best>=0)
  {
    if (bx<tr_px-8)
      *l=TRUE;
    else if (bx>tr_px+8)
      *r=TRUE;
  }
}

U0 TRWriteResult(U8 *path)
{
  U8 *s,*st;
  if (!IsDir("C:/Tmp"))
    DirMk("C:/Tmp");
  if (tr_state==2)
    st="GAME_OVER";
  else
    st="COMPLETE";
  s=MStrPrint("TOKENRAIN RESULT 1\nmode=agent\nseed=%d\nframes=%d\nscore=%d\ncatches=%d\nhits=%d\nlives=%d\nstatus=%s\n",
    tr_seed0,tr_frames,tr_score,tr_catches,tr_hits,tr_lives,st);
  FileWrite(path,s,StrLen(s));
  Free(s);
}

U0 TRAgentSim(U8 *out_file=NULL)
{
  I64 f,l,r;
  if (!out_file)
    out_file="C:/Tmp/TokenRainResult.TXT";
  TRLoadHigh;
  TRReset(TRUE);
  for (f=0;f<900;f++)
  {
    TRAgentInput(&l,&r);
    TRUpdate(1.0/60.0,l,r);
    if (tr_state!=1)
      break;
  }
  if (tr_score>tr_high)
  {
    tr_high=tr_score;
    TRSaveHigh;
  }
  TRWriteResult(out_file);
  tr_state=3;
}

U0 TokenRainAgent(U8 *out_file=NULL)
{
  TRAgentSim(out_file);
}
