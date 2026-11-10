#ifndef SP_STATE_HC
#define SP_STATE_HC

U0 SpInit(CSpoon *s,Bool agent)
{
  I64 i;
  for (i=0;i<SP_MAX;i++)
    s->offers[i].active=FALSE;
  s->spoon_x=320.0;
  s->caught=0;
  s->missed=0;
  s->score=0;
  s->tosses=0;
  s->flash=0;
  s->over=FALSE;
  s->agent=agent;
  s->started=FALSE;
  s->t=0.0;
  s->next_toss=0.7;
  s->over_at=0;
  s->high=SpReadHigh();
  if (agent)
  {
    s->plate=NULL;
    s->piedro=NULL;
  }
  else
  {
    s->plate=SpLoadPlate();
    s->piedro=SpLoadPiedro(64);
    SpSeed(0x51ED);
  }
}

U0 SpReset(CSpoon *s)
{
  I64 i;
  for (i=0;i<SP_MAX;i++)
    s->offers[i].active=FALSE;
  s->spoon_x=320.0;
  s->caught=0;
  s->missed=0;
  s->score=0;
  s->tosses=0;
  s->flash=0;
  s->over=FALSE;
  s->started=TRUE;
  s->t=0.0;
  s->next_toss=0.7;
  s->over_at=0;
}

U0 SpFree(CSpoon *s)
{
  if (s->plate)
    DCDel(s->plate);
  if (s->piedro)
    DCDel(s->piedro);
  Free(s);
}

Bool SpAny(CSpoon *s)
{
  I64 i;
  for (i=0;i<SP_MAX;i++)
    if (s->offers[i].active)
      return TRUE;
  return FALSE;
}

#endif
