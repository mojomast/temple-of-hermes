#ifndef SP_AGENT_HC
#define SP_AGENT_HC

F64 sp_agent_targets[SP_AGENT_TOSSES]={90,170,250,330,410,490,550,300,140,510,220,430};

U0 SpAgentRun(CSpoon *s)
{
  I64 i,next=0;
  F64 t=0.0,dt=1.0/60.0,dx,mv,besty;
  COffer *best;
  SpSeed(0x5EED51A7);
  while (t<45.0)
  {
    if (next<SP_AGENT_TOSSES && t>=next*0.85)
    {
      SpToss(s,sp_agent_targets[next],1.55,next%4);
      next++;
    }
    best=NULL;
    besty=-1.0;
    for (i=0;i<SP_MAX;i++)
      if (s->offers[i].active && s->offers[i].y>besty)
      {
        best=&s->offers[i];
        besty=best->y;
      }
    if (best)
    {
      dx=best->x-s->spoon_x;
      mv=430.0*dt;
      if (dx>mv)
        s->spoon_x=s->spoon_x+mv;
      else if (dx< -mv)
        s->spoon_x=s->spoon_x-mv;
      else
        s->spoon_x=best->x;
      s->spoon_x=Clamp(s->spoon_x,SP_SPOON_MIN,SP_SPOON_MAX);
    }
    SpStep(s,dt);
    t+=dt;
    if (next>=SP_AGENT_TOSSES && !SpAny(s))
      break;
  }
  s->over=TRUE;
  if (s->score>s->high)
    s->high=s->score;
  SpWriteHigh(s->high);
}

#endif
