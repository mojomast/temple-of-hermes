U0 TRSpawn()
{
  I64 i,k;
  for (i=0;i<TR_MAX;i++)
    if (!tr_tok[i].on)
    {
      k=0;
      if (TRRand(100)<34)
        k=1;
      tr_tok[i].x=TR_L+TRRandF()*(TR_R-TR_L);
      tr_tok[i].y=TR_TOP+8;
      tr_tok[i].vy=68.0+TRRandF()*38.0+tr_score*0.55;
      if (tr_tok[i].vy>210.0)
        tr_tok[i].vy=210.0;
      tr_tok[i].kind=k;
      tr_tok[i].on=TRUE;
      return;
    }
}

U0 TRGameOver()
{
  tr_state=2;
  if (tr_score>tr_high)
  {
    tr_high=tr_score;
    TRSaveHigh;
  }
}

U0 TRUpdate(F64 dt,I64 l,I64 r)
{
  I64 i;
  CToken *t;
  F64 dx;
  if (tr_state!=1)
    return;
  if (dt<0)
    dt=0;
  if (dt>0.1)
    dt=0.1;
  tr_frames++;
  if (l)
    tr_px-=270.0*dt;
  if (r)
    tr_px+=270.0*dt;
  if (tr_px<TR_L+30)
    tr_px=TR_L+30;
  if (tr_px>TR_R-30)
    tr_px=TR_R-30;
  tr_spawn-=dt;
  if (tr_spawn<=0)
  {
    TRSpawn;
    tr_spawn=0.82-tr_score*0.0018;
    if (tr_spawn<0.28)
      tr_spawn=0.28;
    tr_spawn+=TRRandF()*0.22;
  }
  for (i=0;i<TR_MAX;i++)
  {
    t=&tr_tok[i];
    if (t->on)
    {
      t->y+=t->vy*dt;
      dx=t->x-tr_px;
      if (dx<0)
        dx=-dx;
      if (t->y+8>=TR_PY && t->y-8<=TR_PY+56 && dx<36.0)
      {
        if (t->kind==0)
        {
          tr_score+=10;
          tr_catches++;
          tr_flash=0.10;
          if (!tr_agent)
            Snd(72);
        }
        else
        {
          tr_lives--;
          tr_hits++;
          tr_score-=12;
          if (tr_score<0)
            tr_score=0;
          tr_flash=0.32;
          if (!tr_agent)
            Snd(45);
        }
        t->on=FALSE;
      }
      else if (t->y>476)
        t->on=FALSE;
    }
  }
  if (tr_lives<=0)
    TRGameOver;
}
