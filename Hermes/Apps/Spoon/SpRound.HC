#ifndef SP_ROUND_HC
#define SP_ROUND_HC

U0 SpMaybeToss(CSpoon *s)
{
  F64 target,tf;
  if (!s->started || s->over)
    return;
  if (s->tosses>=SP_TOSSES)
    return;
  if (s->t<s->next_toss)
    return;
  target=s->spoon_x+SpRandRange(-80,80);
  target=Clamp(target,70.0,570.0);
  tf=1.35+SpRandRange(0,60)/100.0;
  SpToss(s,target,tf,SpRandRange(0,3));
  s->next_toss=s->t+1.05;
}

U0 SpCheckEnd(CSpoon *s)
{
  if (!s->started || s->over)
    return;
  if (s->tosses>=SP_TOSSES && !SpAny(s))
  {
    if (!s->over_at)
      s->over_at=s->t+0.8;
    else if (s->t>=s->over_at)
    {
      s->over=TRUE;
      if (s->score>s->high)
        s->high=s->score;
      SpWriteHigh(s->high);
    }
  }
}

#endif
