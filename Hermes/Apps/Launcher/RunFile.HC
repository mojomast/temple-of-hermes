#ifndef HERMES_APPS_LAUNCHER_RUNFILE_HC
#define HERMES_APPS_LAUNCHER_RUNFILE_HC

CTask *hermes_apps_launcher_task=NULL;

U0 HermesAppsRunFile(U8 *path)
{//Run one app in this task, then restore the launcher window.
  CTask *launcher=hermes_apps_launcher_task;
  CTask *focus;
  I64 i;
  DocTermNew;
  StrCpy(Fs->task_title,"Hermes App");
  Fs->title_src=TTS_LOCKED_CONST;
  Fs->win_inhibit=WIG_USER_TASK_DFT;
  AutoComplete(FALSE);
  WinBorder(TRUE);
  WinMax;
  LBts(&Fs->display_flags,DISPLAYf_SHOW);
  WinToTop;
  WinFocus;
  DocClear;
  Refresh;
  Sleep(150);
  WinToTop;
  WinZBufUpdate;
  if (path)
  {
    if (IsFile(path))
    {
      try
        ExeFile(path);
      catch
        PutExcept;
    }
    Free(path);
  }
  if (TaskValidate(launcher) && launcher!=Fs)
  {
    Sleep(300);
    for (i=0;i<3600;i++)
    {
      focus=sys_focus_task;
      if (!TaskValidate(focus) || focus==launcher || focus==Fs ||
          !Bt(&focus->display_flags,DISPLAYf_SHOW))
        break;
      Sleep(100);
      Yield;
    }
    LBts(&launcher->display_flags,DISPLAYf_SHOW);
    WinToTop(launcher);
    WinFocus(launcher);
    PostMsg(launcher,MSG_KEY_DOWN,0,0);
  }
}

#endif
