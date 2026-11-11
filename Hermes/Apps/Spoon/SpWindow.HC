#ifndef SP_WINDOW_HC
#define SP_WINDOW_HC

U0 SpWindowSetup()
{
  DocTermNew;
  SettingsPush;
  Fs->text_attr=(BLACK<<4)+WHITE;
  MenuPush(
    "File {"
    "  Exit(,CH_ESC);"
    "}"
    "Play {"
    "  Restart(,'\n');"
    "  Left(,,SC_CURSOR_LEFT);"
    "  Right(,,SC_CURSOR_RIGHT);"
    "}"
  );
  AutoComplete(FALSE);
  StrCpy(Fs->task_title,"Spoon");
  Fs->title_src=TTS_LOCKED_CONST;
  Fs->win_inhibit=WIG_USER_TASK_DFT;
  Fs->draw_it=&SpDraw;
  WinBorder(TRUE);
  WinHorz(0,80);
  WinVert(0,60);
  DocCursor;
  DocClear;
  LBts(&Fs->display_flags,DISPLAYf_SHOW);
  WinToTop;
  WinFocus;
  Refresh;
}

#endif
