#ifndef HERMES_APPS_LAUNCHER_LOAD_HC
#define HERMES_APPS_LAUNCHER_LOAD_HC

Cd(__DIR__);;
#include "../Common/Paths.HC"
#include "../Common/Icons.HC"
#include "../Registry.HC"
#include "RunFile.HC"

#define HERMES_LAUNCHER_COLS 6

class CHermesLauncherState
{
  CDC **icons;
  I64 selected;
  I64 icons_loaded;
  U8 *status;
};

U0 HermesAppsLauncherLayout(I64 *x0,I64 *y0,I64 *cw,I64 *ch,I64 w,I64 h)
{
  I64 cols=HERMES_LAUNCHER_COLS,rows,top=48,bottom=32;
  rows=(hermes_apps_num+cols-1)/cols;
  if (rows<1)
    rows=1;
  *cw=(w-16)/cols;
  if (*cw<64)
    *cw=64;
  *x0=((w-cols*(*cw))/2)&~7;
  *ch=((h-top-bottom)/rows)&~7;
  if (*ch>144)
    *ch=144;
  if (*ch<80)
    *ch=80;
  *y0=((h-rows*(*ch))/2)&~7;
  if (*y0<top)
    *y0=top;
}

I64 HermesAppsLauncherHit(I64 w,I64 h,I64 mx,I64 my)
{
  I64 i,x0,y0,cw,ch,x,y;
  HermesAppsRegistryInit;
  HermesAppsLauncherLayout(&x0,&y0,&cw,&ch,w,h);
  for (i=0;i<hermes_apps_num;i++)
  {
    x=x0+(i%HERMES_LAUNCHER_COLS)*cw;
    y=y0+(i/HERMES_LAUNCHER_COLS)*ch;
    if (mx>=x && mx<x+cw && my>=y && my<y+ch)
      return i;
  }
  return -1;
}

U0 HermesAppsLauncherDraw(CTask *task,CDC *dc)
{
  CHermesLauncherState *s=task->user_data(CHermesLauncherState *);
  I64 i,x0,y0,cw,ch,x,y,w,h;
  U8 *title;
  CHermesApp *app;
  if (!s)
    return;
  w=task->pix_width;
  h=task->pix_height;
  dc->color=BLACK;
  GrRect(dc,0,0,w,h);
  dc->color=BLUE;
  GrRect(dc,0,0,w,40);
  dc->color=YELLOW;
  GrPrint(dc,16,8,"THE TEMPLE OF HERMES  v0.1.3");
  dc->color=LTCYAN;
  if (s->status)
    GrPrint(dc,16,24,"%s",s->status);
  else
    GrPrint(dc,16,24,"Apps");
  HermesAppsLauncherLayout(&x0,&y0,&cw,&ch,w,h);
  for (i=0;i<hermes_apps_num;i++)
  {
    app=&hermes_apps[i];
    x=x0+(i%HERMES_LAUNCHER_COLS)*cw;
    y=y0+(i/HERMES_LAUNCHER_COLS)*ch;
    if (i==s->selected)
    {
      dc->color=YELLOW;
      GrBorder(dc,x+4,y+2,x+cw-5,y+ch-5,1,0);
    }
    if (s->icons[i])
      GrBlot(dc,x+(cw-32)/2,y+8,s->icons[i]);
    else
    {
      dc->color=DKGRAY;
      GrRect(dc,x+(cw-32)/2,y+8,32,32);
      dc->color=WHITE;
      GrPrint(dc,x+(cw-32)/2+12,y+20,"?");
    }
    title=app->title;
    if (i==s->selected)
      dc->color=YELLOW;
    else
      dc->color=WHITE;
    GrPrint(dc,(x+(cw-StrLen(title)*FONT_WIDTH)/2)&~7,y+48,"%s",title);
    if (i==s->selected)
      dc->color=WHITE;
    else
      dc->color=LTGRAY;
    GrPrint(dc,(x+(cw-24)/2)&~7,y+72,"[%c]",app->shortcut);
  }
  dc->color=LTCYAN;
  GrPrint(dc,16,h-24,"Click an icon or press its key to open - Esc returns here - F1 help");
}

Bool HermesAppsLauncherSelect(CHermesLauncherState *s,I64 idx)
{
  CHermesApp *app;
  HermesAppsRegistryInit;
  if (idx<0 || idx>=hermes_apps_num)
    return FALSE;
  app=&hermes_apps[idx];
  s->selected=idx;
  if (s->status)
    Free(s->status);
  if (app->run && IsFile(app->run))
  {
    s->status=MStrPrint("Launching %s...",app->title);
    hermes_apps_launcher_task=Fs;
    Spawn(&HermesAppsRunFile,StrNew(app->run),app->title);
    return TRUE;
  }
  if (!StrCmp(app->id,"home-temple"))
    s->status=StrNew("Home.  Choose any icon above.");
  else if (app->planned)
    s->status=MStrPrint("%s is planned but not implemented yet.",app->title);
  else
    s->status=MStrPrint("%s: %s",app->title,app->desc);
  return FALSE;
}

U0 HermesAppsLauncherMove(CHermesLauncherState *s,I64 dx,I64 dy)
{
  I64 col,row,rows;
  if (s->selected<0)
    s->selected=0;
  col=s->selected%HERMES_LAUNCHER_COLS;
  row=s->selected/HERMES_LAUNCHER_COLS;
  rows=(hermes_apps_num+HERMES_LAUNCHER_COLS-1)/HERMES_LAUNCHER_COLS;
  col=(col+dx+HERMES_LAUNCHER_COLS)%HERMES_LAUNCHER_COLS;
  row=(row+dy+rows)%rows;
  s->selected=row*HERMES_LAUNCHER_COLS+col;
  if (s->selected>=hermes_apps_num)
    s->selected=hermes_apps_num-1;
}

Bool HermesAppsLauncherLaunchKey(CHermesLauncherState *s,I64 ch)
{
  I64 i;
  for (i=0;i<hermes_apps_num;i++)
    if (ToUpper(ch)==hermes_apps[i].shortcut)
    {
      s->selected=i;
      return HermesAppsLauncherSelect(s,i);
    }
  return FALSE;
}

U0 HermesAppsLauncherTask(U8 *data)
{
  CHermesLauncherState *s;
  I64 i,msg_code,arg1,arg2,idx,sc;
  Bool launch,did_launch;
  HermesAppsRegistryInit;
  s=CAlloc(sizeof(CHermesLauncherState));
  Fs->user_data=s(I64);
  s->icons=CAlloc(sizeof(CDC*)*hermes_apps_num);
  s->selected=0;
  s->icons_loaded=0;
  s->status=MStrPrint("%d apps and games",hermes_apps_num);
  for (i=0;i<hermes_apps_num;i++)
  {
    s->icons[i]=HermesAppsIcon(hermes_apps[i].icon,32);
    if (s->icons[i])
      s->icons_loaded++;
  }
  DocTermNew;
  SettingsPush;
  AutoComplete(FALSE);
  StrCpy(Fs->task_title,"Hermes Apps");
  Fs->title_src=TTS_LOCKED_CONST;
  Fs->win_inhibit=WIG_USER_TASK_DFT;
  Fs->draw_it=&HermesAppsLauncherDraw;
  WinBorder(FALSE);
  WinMax;
  LBts(&Fs->display_flags,DISPLAYf_SHOW);
  WinToTop;
  WinFocus;
  TaskDerivedValsUpdate(Fs);
  DocClear;
  WinZBufUpdate;
  Refresh;
  if (data)
  {
    for (i=0;i<hermes_apps_num;i++)
      if (!StrCmp(data,hermes_apps[i].id))
      {
        s->selected=i;
        break;
      }
    Free(data);
  }
  while (TRUE)
  {
    msg_code=GetMsg(&arg1,&arg2,1<<MSG_KEY_DOWN|1<<MSG_MS_L_DOWN);
    if (msg_code==MSG_MS_L_DOWN)
    {
      idx=HermesAppsLauncherHit(Fs->pix_width,Fs->pix_height,arg1,arg2);
      if (idx>=0)
      {
        s->selected=idx;
        if (!HermesAppsLauncherSelect(s,idx))
          Refresh;
      }
    }
    else if (msg_code==MSG_KEY_DOWN)
    {
      sc=arg2&0xFFFF;
      launch=FALSE;
      did_launch=FALSE;
      if (sc==SC_CURSOR_LEFT && !arg1)
        HermesAppsLauncherMove(s,-1,0);
      else if (sc==SC_CURSOR_RIGHT && !arg1)
        HermesAppsLauncherMove(s,1,0);
      else if (sc==SC_CURSOR_UP && !arg1)
        HermesAppsLauncherMove(s,0,-1);
      else if (sc==SC_CURSOR_DOWN && !arg1)
        HermesAppsLauncherMove(s,0,1);
      else if (sc==SC_F1 && !arg1)
      {
        for (i=0;i<hermes_apps_num;i++)
          if (!StrCmp(hermes_apps[i].id,"about"))
          {
            s->selected=i;
            launch=TRUE;
            break;
          }
      }
      else if (arg1==CH_CTRLM || arg1=='\n' || arg1==CH_SPACE)
        launch=TRUE;
      else if (arg1==CH_ESC || arg1==CH_SHIFT_ESC || !arg1)
        ;
      else
        did_launch=HermesAppsLauncherLaunchKey(s,arg1);
      if (launch && s->selected>=0)
        did_launch=HermesAppsLauncherSelect(s,s->selected);
      if (!did_launch)
        Refresh;
    }
  }
}

U0 HermesAppsLauncher()
{
  Spawn(&HermesAppsLauncherTask,NULL,"Hermes Apps");
}

U0 HermesAppsOpen(U8 *id)
{
  if (id && *id)
    Spawn(&HermesAppsLauncherTask,StrNew(id),"Hermes Apps");
  else
    HermesAppsLauncher;
}

#endif
