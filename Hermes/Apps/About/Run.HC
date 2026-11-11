Cd(__DIR__);;
#ifndef HERMES_ABOUT_RUN_HC
#define HERMES_ABOUT_RUN_HC

U0 HermesAboutRun()
{//Show the About/help page and wait for Esc.
  I64 ch;
  SettingsPush;
  DocTermNew;
  AutoComplete(FALSE);
  StrCpy(Fs->task_title,"About");
  Fs->title_src=TTS_LOCKED_CONST;
  Fs->win_inhibit=WIG_USER_TASK_DFT;
  WinBorder(TRUE);
  WinMax;
  LBts(&Fs->display_flags,DISPLAYf_SHOW);
  WinToTop;
  WinFocus;
  DocClear;
  Type("::/Doc/AboutHermes.DD");
  "$$FG,LTCYAN$$Press Esc to return to the launcher.$$FG$$\n";
  Refresh;
  while (TRUE)
  {
    ch=ScanChar;
    if (ch==CH_ESC || ch==CH_SHIFT_ESC)
      break;
    Sleep(50);
    Yield;
  }
  SettingsPop;
}

HermesAboutRun;
#endif
