#ifndef SP_DRAW_HC
#define SP_DRAW_HC

U0 SpDraw(CTask *task,CDC *dc)
{
  I64 i,x,y;
  CSpoon *s=task->user_data(CSpoon *);
  COffer *o;
  if (!s)
    return;
  SpDrawBanner(task,dc,s);
  SpDrawHud(task,dc,s);
  dc->color=BLACK;
  GrRect(dc,0,180,task->pix_width,270);
  dc->color=DKGRAY;
  GrBorder(dc,4,180,636,449,1,0);
  dc->color=BLUE;
  GrLine(dc,8,448,632,448);
  if (s->piedro)
    GrBlot(dc,552,182,s->piedro);
  else
  {
    dc->color=BROWN;
    GrRect(dc,552,182,64,64);
  }
  dc->color=YELLOW;
  GrPrint(dc,544,248,"DON PIEDRO");
  GrRect(dc,556,236,6,6);
  for (i=0;i<SP_MAX;i++)
  {
    o=&s->offers[i];
    if (o->active)
    {
      x=ToI64(o->x);
      y=ToI64(o->y);
      SpDrawToken(dc,x,y,o->kind);
    }
  }
  SpDrawSpoon(dc,s->spoon_x);
  if (s->flash>0)
  {
    dc->color=YELLOW;
    GrPrint(dc,ToI64(s->spoon_x)-36,SP_SPOON_Y-28,"For Hermes!");
  }
  if (!s->started)
    SpDrawTitle(dc);
  if (s->over)
    SpDrawOver(dc,s);
}

#endif
