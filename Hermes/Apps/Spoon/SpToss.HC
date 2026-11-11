#ifndef SP_TOSS_HC
#define SP_TOSS_HC

U0 SpToss(CSpoon *s,F64 tx,F64 tflight,I64 kind)
{
  I64 i;
  COffer *o;
  F64 sx=548.0,sy=228.0;
  for (i=0;i<SP_MAX;i++)
    if (!s->offers[i].active)
      break;
  if (i>=SP_MAX)
    return;
  o=&s->offers[i];
  o->active=TRUE;
  o->kind=kind;
  o->x=sx;
  o->y=sy;
  o->vx=(tx-sx)/tflight;
  o->vy=(SP_SPOON_Y-sy-0.5*SP_G*tflight*tflight)/tflight;
  o->spin=SpRandRange(0,360)+0.0;
  s->tosses++;
}

U0 SpStep(CSpoon *s,F64 dt)
{
  I64 i;
  COffer *o;
  if (s->flash>0)
    s->flash--;
  for (i=0;i<SP_MAX;i++)
  {
    o=&s->offers[i];
    if (o->active)
    {
      o->vy=o->vy+240.0*dt;
      o->x=o->x+o->vx*dt;
      o->y=o->y+o->vy*dt;
      o->spin=o->spin+180.0*dt;
      if (o->y>=SP_SPOON_Y-6 && o->y<=SP_SPOON_Y+20 && Abs(o->x-s->spoon_x)<42.0)
      {
        o->active=FALSE;
        s->caught++;
        s->score=s->score+10;
        s->flash=10;
      }
      else if (o->y>470.0)
      {
        o->active=FALSE;
        s->missed++;
      }
    }
  }
}

#endif
