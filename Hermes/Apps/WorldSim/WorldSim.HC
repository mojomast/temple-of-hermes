// WorldSim - a living world of Hermes agents.
// Part of THE TEMPLE OF HERMES.  Public domain / Unlicense.
//
// The world is a small tile planet.  Five agents explore it, gather
// resources, and report what they find in the event log.  The icon and
// palette come from Hermes/Art (32x32 worldsim sprite).

Cd(__DIR__);;
#include "WorldSimArt"

#define WS_MAP_W       40
#define WS_MAP_H       24
#define WS_MAX_AGENTS  5
#define WS_LOG_LINES   8
#define WS_LOG_COLS    88

#define T_OCEAN   0
#define T_PLAIN   1
#define T_FOREST  2
#define T_HILL    3
#define T_MOUNT   4
#define T_CITY    5

class CAgent
{
  I64 x,y,home_x,home_y;
  I64 energy,score,color;
  U8 *name;
};

CAgent ws_agents[WS_MAX_AGENTS];
I64 ws_world[WS_MAP_H][WS_MAP_W];
I64 ws_res[WS_MAP_H][WS_MAP_W];
U8 ws_log[WS_LOG_LINES][WS_LOG_COLS];
I64 ws_log_head,ws_log_cnt;
I64 ws_seed,ws_tick,ws_paused,ws_speed,ws_sel,ws_running;
F64 ws_step_time;
CTask *ws_anim_task;

U8 *ws_names[WS_MAX_AGENTS] =
{
  "ATHENA","HERMES","NOUS","ORACLE","DAEDALUS"
};

I64 ws_colors[WS_MAX_AGENTS] =
{
  LTCYAN,YELLOW,LTGREEN,LTPURPLE,LTRED
};

U0 WsLog(U8 *st)
{
  StrCpy(ws_log[ws_log_head],st);
  ws_log[ws_log_head][WS_LOG_COLS-1]=0;
  ws_log_head=(ws_log_head+1)%WS_LOG_LINES;
  if (ws_log_cnt<WS_LOG_LINES)
    ws_log_cnt++;
}

U0 WsLogFmt(U8 *fmt,...)
{
  U8 *st=StrPrintJoin(NULL,fmt,argc,argv);
  WsLog(st);
  Free(st);
}

I64 WsTerrainColor(I64 t)
{
  switch (t)
  {
  case T_OCEAN:  return BLUE;
  case T_PLAIN:  return GREEN;
  case T_FOREST: return LTGREEN;
  case T_HILL:   return BROWN;
  case T_MOUNT:  return LTGRAY;
  case T_CITY:   return YELLOW;
  }
  return BLUE;
}

U8 *WsTerrainName(I64 t)
{
  switch (t)
  {
  case T_OCEAN:  return "ocean";
  case T_PLAIN:  return "plain";
  case T_FOREST: return "forest";
  case T_HILL:   return "hill";
  case T_MOUNT:  return "mountain";
  case T_CITY:   return "city";
  }
  return "unknown";
}

U0 WsDrawArt(CDC *dc,I64 x,I64 y,I64 w,I64 h,U8 *img,I64 scale=1)
{
  I64 i,j,c;
  for (j=0;j<h;j++)
    for (i=0;i<w;i++)
    {
      c=img[j*w+i];
      if (c)
      {
        dc->color=c;
        GrRect(dc,x+i*scale,y+j*scale,scale,scale);
      }
    }
}

U0 WsGenWorld()
{
  I64 i,j,k,cx,cy,r,dx,dy,d2,hgt,land,city_x=-1,city_y=-1;
  Seed(ws_seed);
  for (j=0;j<WS_MAP_H;j++)
    for (i=0;i<WS_MAP_W;i++)
    {
      ws_world[j][i]=T_OCEAN;
      ws_res[j][i]=0;
    }

  // Raise a handful of overlapping land masses.
  for (k=0;k<9;k++)
  {
    cx=RandU16%WS_MAP_W;
    cy=RandU16%WS_MAP_H;
    r=5+RandU16%8;
    for (j=0;j<WS_MAP_H;j++)
      for (i=0;i<WS_MAP_W;i++)
      {
        dx=i-cx;
        dy=(j-cy)*2;
        d2=dx*dx+dy*dy;
        if (d2<r*r)
        {
          hgt=r*r-d2;
          ws_res[j][i]+=hgt;
        }
      }
  }

  for (j=0;j<WS_MAP_H;j++)
    for (i=0;i<WS_MAP_W;i++)
    {
      hgt=ws_res[j][i];
      ws_res[j][i]=0;
      if (hgt<=0)
        ws_world[j][i]=T_OCEAN;
      else if (hgt<18)
        ws_world[j][i]=T_PLAIN;
      else if (hgt<56)
        ws_world[j][i]=T_FOREST;
      else if (hgt<110)
        ws_world[j][i]=T_HILL;
      else
        ws_world[j][i]=T_MOUNT;
    }

  // Find a pleasant place for the city and scatter resources.
  for (j=2;j<WS_MAP_H-3 && city_x<0;j++)
    for (i=2;i<WS_MAP_W-3 && city_x<0;i++)
      if (ws_world[j][i]==T_PLAIN)
      {
        city_x=i;
        city_y=j;
      }
  if (city_x<0)
  {
    city_x=WS_MAP_W/2;
    city_y=WS_MAP_H/2;
    ws_world[city_y][city_x]=T_PLAIN;
  }
  ws_world[city_y][city_x]=T_CITY;
  ws_res[city_y][city_x]=20;

  land=0;
  for (j=0;j<WS_MAP_H;j++)
    for (i=0;i<WS_MAP_W;i++)
    {
      if (ws_world[j][i]!=T_OCEAN)
        land++;
      if (ws_world[j][i]!=T_OCEAN && RandU16%100<16)
        ws_res[j][i]=1+RandU16%9;
    }

  for (k=0;k<WS_MAX_AGENTS;k++)
  {
    I64 tries=0;
    do
    {
      i=RandU16%WS_MAP_W;
      j=RandU16%WS_MAP_H;
      tries++;
    }
    while (ws_world[j][i]==T_OCEAN && tries<1000);
    ws_agents[k].x=i;
    ws_agents[k].y=j;
    ws_agents[k].home_x=i;
    ws_agents[k].home_y=j;
    ws_agents[k].energy=70+RandU16%31;
    ws_agents[k].score=0;
    ws_agents[k].color=ws_colors[k];
    ws_agents[k].name=ws_names[k];
  }

  ws_tick=0;
  ws_log_head=0;
  ws_log_cnt=0;
  WsLogFmt("World %d: %d land tiles",ws_seed,land);
  WsLog("Agents awake. Space pauses.");
}

U0 WsCollect(I64 a)
{
  CAgent *ag=&ws_agents[a];
  I64 g;
  if (ag->x<0 || ag->x>=WS_MAP_W || ag->y<0 || ag->y>=WS_MAP_H)
    return;
  g=ws_res[ag->y][ag->x];
  if (g>0)
  {
    ws_res[ag->y][ag->x]=0;
    ag->score+=g;
    ag->energy=MinI64(100,ag->energy+g*2);
    WsLogFmt("%s gathered %d at (%d,%d)",ag->name,g,ag->x,ag->y);
  }
}

U0 WsMove(I64 a,I64 dx,I64 dy)
{
  CAgent *ag=&ws_agents[a];
  I64 nx=ag->x+dx,ny=ag->y+dy;
  if (nx<0 || nx>=WS_MAP_W || ny<0 || ny>=WS_MAP_H)
    return;
  if (ws_world[ny][nx]==T_OCEAN)
    return;
  ag->x=nx;
  ag->y=ny;
  WsCollect(a);
}

U0 WsFindResource(I64 a,I64 *dx,I64 *dy)
{
  CAgent *ag=&ws_agents[a];
  I64 i,j,best=0,bx=0,by=0,d,v;
  for (j=ag->y-3;j<=ag->y+3;j++)
    for (i=ag->x-3;i<=ag->x+3;i++)
      if (i>=0 && i<WS_MAP_W && j>=0 && j<WS_MAP_H)
      {
        v=ws_res[j][i];
        if (v>0)
        {
          d=AbsI64(i-ag->x)+AbsI64(j-ag->y)+1;
          v=v*16/d;
          if (v>best)
          {
            best=v;
            bx=i;
            by=j;
          }
        }
      }
  if (best)
  {
    *dx=SignI64(bx-ag->x);
    *dy=SignI64(by-ag->y);
  }
  else
  {
    *dx=0;
    *dy=0;
  }
}

U0 WsAgentStep(I64 a)
{
  CAgent *ag=&ws_agents[a];
  I64 dx,dy,r;
  if (ag->energy<=0)
  {
    ag->x=ag->home_x;
    ag->y=ag->home_y;
    ag->energy=40;
    WsLogFmt("%s returned to the city",ag->name);
    return;
  }
  WsFindResource(a,&dx,&dy);
  if (!dx && !dy)
  {
    r=RandU16%4;
    if (r==0)
      dx=1;
    else if (r==1)
      dx=-1;
    else if (r==2)
      dy=1;
    else
      dy=-1;
  }
  WsMove(a,dx,dy);
  ag->energy-=1;
  if (ws_world[ag->y][ag->x]==T_CITY && ag->energy<60)
    ag->energy=MinI64(100,ag->energy+5);
}

U0 WsStep()
{
  I64 a,i,j,k;
  ws_tick++;
  for (a=0;a<WS_MAX_AGENTS;a++)
    WsAgentStep(a);

  if (ws_tick%7==0)
  {
    for (k=0;k<20;k++)
    {
      j=RandU16%WS_MAP_H;
      i=RandU16%WS_MAP_W;
      if (ws_world[j][i]!=T_OCEAN && ws_res[j][i]==0)
      {
        ws_res[j][i]=1+RandU16%6;
        break;
      }
    }
  }
}

U0 WsDrawMap(CDC *dc,I64 mx,I64 my,I64 tile)
{
  I64 i,j,c;
  for (j=0;j<WS_MAP_H;j++)
    for (i=0;i<WS_MAP_W;i++)
    {
      c=WsTerrainColor(ws_world[j][i]);
      dc->color=c;
      GrRect(dc,mx+i*tile,my+j*tile,tile-1,tile-1);
      if (ws_res[j][i]>0)
      {
        dc->color=YELLOW;
        GrRect(dc,mx+i*tile+tile/2-1,my+j*tile+tile/2-1,2,2);
      }
      if (ws_world[j][i]==T_MOUNT)
      {
        dc->color=WHITE;
        GrPlot(dc,mx+i*tile+tile/2,my+j*tile+2);
      }
    }
}

U0 WsDrawAgents(CDC *dc,I64 mx,I64 my,I64 tile)
{
  I64 a,cx,cy,d;
  for (a=0;a<WS_MAX_AGENTS;a++)
  {
    cx=mx+ws_agents[a].x*tile+tile/2;
    cy=my+ws_agents[a].y*tile+tile/2;
    d=tile-3;
    if (d<3)
      d=3;
    dc->color=BLACK;
    GrFillCircle(dc,cx,cy,,d+2);
    dc->color=ws_agents[a].color;
    GrFillCircle(dc,cx,cy,,d);
    if (a==ws_sel)
    {
      dc->color=WHITE;
      GrCircle(dc,cx,cy,d/2+3);
    }
  }
}

U0 WsDrawPanel(CDC *dc,I64 px,I64 py,I64 pw,I64 ph)
{
  I64 a,cy,y,bw;
  CAgent *ag=&ws_agents[ws_sel];
  dc->color=DKGRAY;
  GrRect(dc,px,py,pw,ph);
  dc->color=YELLOW;
  GrPrint(dc,px+6,py+5,"AGENTS");
  cy=py+22;
  for (a=0;a<WS_MAX_AGENTS;a++)
  {
    dc->color=ws_agents[a].color;
    GrFillCircle(dc,px+10,cy+4,,7);
    if (a==ws_sel)
      dc->color=WHITE;
    else
      dc->color=LTGRAY;
    GrPrint(dc,px+20,cy,"%s",ws_agents[a].name);
    cy+=14;
  }

  y=cy+10;
  dc->color=LTGRAY;
  GrPrint(dc,px+6,y,"SELECTED");
  y+=14;
  dc->color=ag->color;
  GrPrint(dc,px+6,y,"%s",ag->name);
  y+=16;

  dc->color=LTGRAY;
  GrPrint(dc,px+6,y,"Energy");
  y+=12;
  bw=pw-12;
  dc->color=BLACK;
  GrRect(dc,px+6,y,bw,8);
  if (ag->energy>50)
    dc->color=LTGREEN;
  else if (ag->energy>25)
    dc->color=YELLOW;
  else
    dc->color=LTRED;
  GrRect(dc,px+6,y,bw*ag->energy/100,8);
  y+=16;

  dc->color=LTGRAY;
  GrPrint(dc,px+6,y,"Cargo %d",ag->score);
  y+=12;
  GrPrint(dc,px+6,y,"At %d,%d",ag->x,ag->y);
  y+=12;
  GrPrint(dc,px+6,y,"%s",WsTerrainName(ws_world[ag->y][ag->x]));
  y+=22;

  if (ws_paused)
  {
    dc->color=LTRED;
    GrPrint(dc,px+6,y,"PAUSED");
  }
  else
  {
    dc->color=LTGREEN;
    GrPrint(dc,px+6,y,"RUNNING");
  }
  y+=12;
  dc->color=LTGRAY;
  GrPrint(dc,px+6,y,"Speed %d",ws_speed);
  y+=12;
  GrPrint(dc,px+6,y,"Tick %d",ws_tick);
}

U0 WsDrawLog(CDC *dc,I64 lx,I64 ly,I64 lw,I64 lh)
{
  I64 k,idx,y;
  dc->color=DKGRAY;
  GrRect(dc,lx,ly,lw,lh);
  dc->color=LTCYAN;
  GrPrint(dc,lx+6,ly+5,"EVENT LOG");
  y=ly+20;
  for (k=0;k<ws_log_cnt;k++)
  {
    idx=(ws_log_head-ws_log_cnt+k+WS_LOG_LINES*2)%WS_LOG_LINES;
    if (k==ws_log_cnt-1)
      dc->color=WHITE;
    else
      dc->color=LTGRAY;
    GrPrint(dc,lx+8,y,"%s",ws_log[idx]);
    y+=11;
  }
  if (lh>40)
  {
    dc->color=CYAN;
    GrPrint(dc,lx+6,ly+lh-15,
      "Space pause  R new world  Tab next  1-5 select  Arrows move  +/- speed  Esc quit");
  }
}

U0 WsDrawIt(CTask *task,CDC *dc)
{
  I64 w=task->pix_width,h=task->pix_height;
  I64 pad=8,header=48,panel_w=136;
  I64 avail_w,avail_h,tile,mw,mh,mx,my,px,py,pw,ph,lx,ly,lw,lh;
  dc->color=BLACK;
  GrRect(dc,0,0,w,h);

  dc->color=BLUE;
  GrRect(dc,0,0,w,header);
  WsDrawArt(dc,8,7,32,32,worldsim_icon,1);
  dc->color=YELLOW;
  GrPrint(dc,48,7,"WORLDSIM");
  dc->color=LTCYAN;
  GrPrint(dc,48,21,"Hermes agent worlds  -  tick %d",ws_tick);
  dc->color=LTGRAY;
  GrPrint(dc,w-150,21,"seed %d",ws_seed);

  avail_w=w-2*pad-panel_w-8;
  avail_h=h-header-pad*2-96;
  tile=MinI64(avail_w/WS_MAP_W,avail_h/WS_MAP_H);
  if (tile<6)
    tile=6;
  if (tile>18)
    tile=18;
  mw=WS_MAP_W*tile;
  mh=WS_MAP_H*tile;
  mx=pad;
  my=header;
  px=mx+mw+8;
  py=my;
  pw=w-px-pad;
  ph=mh;
  lx=pad;
  ly=my+mh+8;
  lw=w-2*pad;
  lh=h-ly-pad;

  if (pw<80)
  {
    pw=80;
    px=w-pw-pad;
  }
  if (lh<24)
    lh=24;

  WsDrawMap(dc,mx,my,tile);
  WsDrawAgents(dc,mx,my,tile);
  WsDrawPanel(dc,px,py,pw,ph);
  WsDrawLog(dc,lx,ly,lw,lh);
}

U0 WsAnimateTask(I64)
{
  while (ws_running)
  {
    Sleep(ws_speed);
    if (!ws_paused)
      WsStep;
    Refresh;
  }
}

U0 WsInit()
{
  I64 a;
  ws_seed=RandU16;
  if (!ws_seed)
    ws_seed=1;
  ws_paused=FALSE;
  ws_speed=140;
  ws_sel=0;
  ws_running=TRUE;
  WsGenWorld;
  for (a=0;a<WS_MAX_AGENTS;a++)
    ws_agents[a].energy=MinI64(100,ws_agents[a].energy);
}

U0 WsReset()
{
  ws_seed=RandU16;
  if (!ws_seed)
    ws_seed=1;
  WsGenWorld;
}

U0 WorldSim()
{
  I64 ch,sc;
  SettingsPush;
  Fs->text_attr=BLACK<<4+WHITE;
  MenuPush(
    "File {"
    "  Exit(,CH_ESC);"
    "}"
    "World {"
    "  New(,'R');"
    "  Pause(,' ');"
    "  NextAgent(,,SC_TAB);"
    "}"
  );
  AutoComplete(0);
  WinBorder;
  WinMax;
  DocCursor;
  DocClear;
  WsInit;
  Fs->draw_it=&WsDrawIt;
  ws_anim_task=Spawn(&WsAnimateTask,NULL,"WorldSim Anim",,Fs);
  TaskDerivedValsUpdate(Fs);
  WinZBufUpdate;

  try
  {
    while (ws_running)
    {
      ch=GetKey(&sc);
      if (ch==CH_ESC || ch==CH_SHIFT_ESC)
        break;
      switch (ch)
      {
      case ' ':
        ws_paused=!ws_paused;
        break;
      case 'R':
      case 'r':
        WsReset;
        break;
      case '+':
      case '=':
        ws_speed=MaxI64(40,ws_speed-20);
        break;
      case '-':
        ws_speed=MinI64(500,ws_speed+20);
        break;
      case '\t':
        ws_sel=(ws_sel+1)%WS_MAX_AGENTS;
        break;
      case '1':case '2':case '3':case '4':case '5':
        ws_sel=ch-'1';
        break;
      default:
        switch (sc.u8[0])
        {
        case SC_CURSOR_LEFT:
          WsMove(ws_sel,-1,0);
          break;
        case SC_CURSOR_RIGHT:
          WsMove(ws_sel,1,0);
          break;
        case SC_CURSOR_UP:
          WsMove(ws_sel,0,-1);
          break;
        case SC_CURSOR_DOWN:
          WsMove(ws_sel,0,1);
          break;
        }
      }
    }
  }
  catch
    PutExcept;

  ws_running=FALSE;
  if (ws_anim_task)
    Kill(ws_anim_task);
  Fs->draw_it=NULL;
  MenuPop;
  SettingsPop;
  DocClear;
}

WorldSim;
