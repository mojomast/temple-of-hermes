// WindowLoop.HC - a spawned task that leaves on Esc.
U0 DemoLoopTask(U8 *unused)
{
  I64 msg,a1,a2;
  DocTermNew;
  SettingsPush;
  StrCpy(Fs->task_title,"Demo");
  Fs->win_inhibit=WIG_USER_TASK_DFT;
  WinBorder(TRUE);
  WinMax;
  LBts(&Fs->display_flags,DISPLAYf_SHOW);
  WinToTop;
  WinFocus;
  while (TRUE)
  {
    msg=GetMsg(&a1,&a2,1<<MSG_KEY_DOWN);
    if (msg==MSG_KEY_DOWN && (a1==CH_ESC || a1==CH_SHIFT_ESC))
      break;
    Yield;
  }
  GetMsg(,,1<<MSG_KEY_UP);
  SettingsPop;
}

U0 DemoLoop()
{
  Spawn(&DemoLoopTask,NULL,"Demo");
}
