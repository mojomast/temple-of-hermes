// On-screen driver banner and a second AGENT cursor.

U0 HermesWallPaper(CTask *_task)
{
  U8 *mode,line[80];
  I64 attr;
  if (hermes_old_wall)
    (*hermes_old_wall)(_task);
  mode=HermesModeName;
  switch (hermes_mode)
  {
  case HERMES_MODE_AGENT:
    attr=RED<<4+YELLOW;
    break;
  case HERMES_MODE_SHARED:
    attr=CYAN<<4+BLACK;
    break;
  default:
    attr=GREEN<<4+BLACK;
    break;
  }
  StrPrint(line," HERMES/%-6s ",mode);
  TextPrint(Fs,0,0,attr,"%s",line);
  StrPrint(line," THE TEMPLE OF HERMES  [%s]  v%s ",mode,HERMES_VERSION);
  TextPrint(Fs,0,TEXT_ROWS-1,attr,"%s",line);
}

U0 HermesDrawMs(CDC *dc,I64 x,I64 y)
{
  I64 old_color,old_thick;
  I64 ax,ay;
  if (hermes_mode==HERMES_MODE_AGENT)
  {
    hermes_agent_mx=ms.pos.x;
    hermes_agent_my=ms.pos.y;
  }
  if (hermes_old_ms)
    (*hermes_old_ms)(dc,x,y);
  if (hermes_mode==HERMES_MODE_USER)
    return;
  ax=hermes_agent_mx;
  ay=hermes_agent_my;
  old_color=dc->color;
  old_thick=dc->thick;
  dc->flags&=~(DCF_TRANSFORMATION|DCF_SYMMETRY);
  dc->thick=2;
  if (hermes_mode==HERMES_MODE_AGENT)
    dc->color=YELLOW;
  else
    dc->color=LTCYAN;
  // Distinct chevron / crosshair, not the user's black arrow.
  GrLine3(dc,ax-7,ay,0,ax+7,ay,0);
  GrLine3(dc,ax,ay-7,0,ax,ay+7,0);
  GrCircle(dc,ax,ay,6);
  dc->color=RED;
  GrArrow3(dc,ax+10,ay+10,0,ax+1,ay+1,0,2.0);
  dc->color=old_color;
  dc->thick=old_thick;
}

U0 HermesPresenceInstall()
{
  if (!hermes_old_wall && gr.fp_wall_paper!=&HermesWallPaper)
    hermes_old_wall=gr.fp_wall_paper;
  gr.fp_wall_paper=&HermesWallPaper;
  if (!hermes_old_ms && gr.fp_draw_ms!=&HermesDrawMs)
    hermes_old_ms=gr.fp_draw_ms;
  gr.fp_draw_ms=&HermesDrawMs;
}

U0 HermesSetMode(I64 mode)
{
  U8 buf[32];
  if (mode!=HERMES_MODE_USER &&
      mode!=HERMES_MODE_SHARED &&
      mode!=HERMES_MODE_AGENT)
    return;
  if (mode==hermes_mode)
    return;
  hermes_mode=mode;
  if (mode==HERMES_MODE_AGENT)
  {
    hermes_agent_mx=ms.pos.x;
    hermes_agent_my=ms.pos.y;
  }
  StrPrint(buf,"%s",HermesModeName);
  HermesEventPush("mode_changed",buf);
}
