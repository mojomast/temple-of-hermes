#ifndef HERMES_APPS_LAUNCHER_LOAD_HC
#define HERMES_APPS_LAUNCHER_LOAD_HC

Cd(__DIR__);;
#include "../Common/Paths.HC"
#include "../Common/Icons.HC"
#include "../Registry.HC"

class CHermesLauncherState
{
  CDC **icons;
  I64 selected;
  I64 icons_loaded;
  U8 *status;
};

U0 HermesAppsLauncherLayout(I64 *x0,I64 *y0,I64 *cw,I64 *ch,I64 w,I64 h)
{
  I64 cols=3,rows;
  rows=(hermes_apps_num+cols-1)/cols;
  *cw=176;
  *ch=80;
  *x0=((w-cols*(*cw))/2)&~7;
  *y0=56;
  if (*y0+rows*(*ch)>h-28)
    *ch=(h-28-*y0)/rows;
  if (*ch<48)
    *ch=48;
}

I64 HermesAppsLauncherHit(I64 w,I64 h,I64 mx,I64 my)
{
  I64 i,x0,y0,cw,ch,x,y;
  HermesAppsRegistryInit;
  HermesAppsLauncherLayout(&x0,&y0,&cw,&ch,w,h);
  for (i=0;i<hermes_apps_num;i++)
  {
    x=x0+(i%3)*cw;
    y=y0+(i/3)*ch;
    if (mx>=x && mx<x+cw && my>=y && my<y+ch)
      return i;
  }
  return -1;
}

U0 HermesAppsLauncherDraw(CTask *task,CDC *dc)
{
  CHermesLauncherState *s=task->user_data(CHermesLauncherState *);
  I64 i,j,x0,y0,cw,ch,x,y,w,h;
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
  GrPrint(dc,16,8,"THE TEMPLE OF HERMES");
  dc->color=LTCYAN;
  GrPrint(dc,16,24,"Apps");
  HermesAppsLauncherLayout(&x0,&y0,&cw,&ch,w,h);
  for (i=0;i<hermes_apps_num;i++)
  {
    app=&hermes_apps[i];
    j=i%3;
    x=x0+j*cw;
    y=y0+(i/3)*ch;
    if (i==s->selected)
    {
      dc->color=YELLOW;
      GrBorder(dc,x+2,y-2,x+cw-4,y+ch-12,1,0);
    }
    if (s->icons[i])
      GrBlot(dc,x+(cw-32)/2,y,s->icons[i]);
    else
    {
      dc->color=DKGRAY;
      GrRect(dc,x+(cw-32)/2,y,32,32);
      dc->color=WHITE;
      GrPrint(dc,x+(cw-32)/2+12,y+12,"?");
    }
    title=app->title;
    if (i==s->selected)
      dc->color=YELLOW;
    else
      dc->color=WHITE;
    GrPrint(dc,(x+(cw-StrLen(title)*FONT_WIDTH)/2)&~7,y+40,"%s",title);
  }
  dc->color=LTGREEN;
  GrPrint(dc,16,h-24,"Art icons: %d/%d",s->icons_loaded,hermes_apps_num);
  dc->color=WHITE;
  if (s->status)
    GrPrint(dc,16,h-16,"%s",s->status);
}

U0 HermesAppsRunFile(U8 *path)
{//Run an app's Run.HC in its own task.  Used only when a future app exists.
  if (path)
  {
    if (IsFile(path))
      ExeFile(path);
    Free(path);
  }
}

U0 HermesAppsLauncherSelect(CHermesLauncherState *s,I64 idx)
{
  CHermesApp *app;
  U8 *st;
  HermesAppsRegistryInit;
  if (idx<0 || idx>=hermes_apps_num)
    return;
  app=&hermes_apps[idx];
  s->selected=idx;
  if (s->status)
    Free(s->status);
  if (app->run && IsFile(app->run))
  {
    st=MStrPrint("%s: launching %s",app->title,app->run);
    Spawn(&HermesAppsRunFile,StrNew(app->run),app->title);
  }
  else if (app->planned)
    st=MStrPrint("%s is planned but not implemented yet.",app->title);
  else if (!StrCmp(app->id,"home-temple"))
    st=StrNew("Home.  The Temple of Hermes is ready.");
  else
    st=MStrPrint("%s: %s",app->title,app->desc);
  s->status=st;
}

U0 HermesAppsLauncherTask(U8 *data)
{
  CHermesLauncherState *s;
  I64 i,msg_code,arg1,arg2,idx;
  HermesAppsRegistryInit;
  s=CAlloc(sizeof(CHermesLauncherState));
  Fs->user_data=s(I64);
  s->icons=CAlloc(sizeof(CDC*)*hermes_apps_num);
  s->selected=-1;
  s->icons_loaded=0;
  s->status=StrNew("Click an icon or press 1-9.  ESC closes.");
  for (i=0;i<hermes_apps_num;i++)
  {
    s->icons[i]=HermesAppsIcon(hermes_apps[i].icon,32);
    if (s->icons[i])
      s->icons_loaded++;
  }
  if (data)
  {
    for (i=0;i<hermes_apps_num;i++)
      if (!StrCmp(data,hermes_apps[i].id))
      {
        HermesAppsLauncherSelect(s,i);
        break;
      }
    Free(data);
  }
  DocTermNew;
  SettingsPush;
  AutoComplete(FALSE);
  StrCpy(Fs->task_title,"Hermes Apps");
  Fs->title_src=TTS_LOCKED_CONST;
  Fs->win_inhibit=WIG_USER_TASK_DFT;
  Fs->draw_it=&HermesAppsLauncherDraw;
  WinBorder(TRUE);
  WinHorz(4,76);
  WinVert(5,48);
  LBts(&Fs->display_flags,DISPLAYf_SHOW);
  WinToTop;
  WinFocus;
  DocClear;
  Refresh;
  while (TRUE)
  {
    msg_code=GetMsg(&arg1,&arg2,1<<MSG_KEY_DOWN|1<<MSG_MS_L_DOWN);
    if (msg_code==MSG_MS_L_DOWN)
    {
      idx=HermesAppsLauncherHit(Fs->pix_width,Fs->pix_height,arg1,arg2);
      if (idx>=0)
      {
        HermesAppsLauncherSelect(s,idx);
        Refresh;
      }
    }
    else if (msg_code==MSG_KEY_DOWN)
    {
      if (arg1==CH_ESC || arg1==CH_SHIFT_ESC)
        break;
      if (arg1>='1' && arg1<='9')
      {
        idx=arg1-'1';
        if (idx<hermes_apps_num)
        {
          HermesAppsLauncherSelect(s,idx);
          Refresh;
        }
      }
      else if ((arg1==CH_CTRLM || arg1=='\n') && s->selected>=0)
      {
        HermesAppsLauncherSelect(s,s->selected);
        Refresh;
      }
    }
  }
  GetMsg(,,1<<MSG_KEY_UP);
  for (i=0;i<hermes_apps_num;i++)
    if (s->icons[i])
      DCDel(s->icons[i]);
  Free(s->icons);
  if (s->status)
    Free(s->status);
  Free(s);
  Fs->user_data=0;
  SettingsPop;
  Refresh;
}

U0 HermesAppsLauncher()
{//Open the Hermes app launcher in a new window.
  Spawn(&HermesAppsLauncherTask,NULL,"Hermes Apps");
}

U0 HermesAppsOpen(U8 *id)
{//Open the launcher focused on an app id (used by PersonalMenu).
  if (id && *id)
    Spawn(&HermesAppsLauncherTask,StrNew(id),"Hermes Apps");
  else
    HermesAppsLauncher;
}

#endif
