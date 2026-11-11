// Psyche - a small text signal-field monitor for THE TEMPLE OF HERMES.

public U0 PsycheApp()
{
  I64 ch,frame=0;
  Bool paused=FALSE;
  SettingsPush;
  DocTermNew;
  AutoComplete(FALSE);
  StrCpy(Fs->task_title,"Psyche");
  Fs->title_src=TTS_LOCKED_CONST;
  Fs->win_inhibit=WIG_USER_TASK_DFT;
  WinBorder(TRUE);
  WinMax;
  LBts(&Fs->display_flags,DISPLAYf_SHOW);
  WinToTop;
  WinFocus;
  DocClear;
  "PSYCHE\n";
  "SIGNAL FIELD - VISUALIZATION ONLY\n";
  "NO NETWORK   NO TRAINING\n\n";
  "SPACE pause   R reseed   ESC exit\n\n";
  Refresh;
  while (TRUE)
  {
    ch=ScanChar;
    if (ch==CH_ESC || ch==CH_SHIFT_ESC)
      break;
    if (ch==CH_SPACE)
      paused=!paused;
    if (ch=='r' || ch=='R')
    {
      frame=0;
      paused=FALSE;
    }
    if (!paused)
      frame++;
    if ((frame&7)==0)
    {
      DocClear;
      "PSYCHE\n";
      "SIGNAL FIELD - VISUALIZATION ONLY\n";
      "NO NETWORK   NO TRAINING\n\n";
      "SPACE pause   R reseed   ESC exit\n\n";
      "FRAME %05d\n",frame;
      if (paused)
        "PAUSED\n";
      Refresh;
    }
    Sleep(50);
    Yield;
  }
  SettingsPop;
}

PsycheApp;
