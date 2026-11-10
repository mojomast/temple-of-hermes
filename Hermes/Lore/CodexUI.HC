U0 CodexTask(U8 *data)
{
  I64 ch,sc;
  SettingsPush;
  WinBorder;
  WinMax;
  LBts(&Fs->display_flags,DISPLAYf_SHOW);
  WinToTop;
  WinFocus;
  WinZBufUpdate;
  MenuPush(
    "File {"
    "  Exit(,CH_ESC);"
    "}"
  );
  DocClear;
  DocScroll(TRUE);
  DocCursor(TRUE);
  CodexPart0();
  CodexPart1();
  CodexPart2();
  CodexPart3();
  CodexPart4();
  CodexPart5();
  CodexPart6();
  DocTop;
  try
  {
    while (TRUE)
    {
      ch=GetKey(&sc);
      if (ch==CH_ESC || ch==CH_SHIFT_ESC)
        break;
      if (!ch)
        DocPutKey(Fs->put_doc,ch,sc);
    }
  }
  catch PutExcept;
  MenuPop;
  SettingsPop;
}
