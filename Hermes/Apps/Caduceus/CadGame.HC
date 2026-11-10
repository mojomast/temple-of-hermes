U0 Caduceus(Bool agent=FALSE)
{
  I64 ch,sc;
  if (agent) {
    CaduceusAgent(NULL);
    return;
  }
  SettingsPush;
  Fs->text_attr=YELLOW<<4+BLUE;
  PaletteSetStd;
  AutoComplete;
  WinBorder;
  WinMax;
  DocCursor;
  DocClear;
  MenuPush(
  "File {"
  "  Abort(,CH_SHIFT_ESC);"
  "  Exit(,CH_ESC);"
  "}"
  "Play {"
  "  Restart(,'\n');"
  "  Up(,,SC_CURSOR_UP);"
  "  Down(,,SC_CURSOR_DOWN);"
  "  Left(,,SC_CURSOR_LEFT);"
  "  Right(,,SC_CURSOR_RIGHT);"
  "}"
  );
  CadLoadArt();
  CadReset();
  cad_sound=TRUE;
  Fs->song_task=Spawn(&CadSongTask,NULL,"CadSong",,Fs);
  Fs->animate_task=Spawn(&CadAnimateTask,NULL,"CadAnim",,Fs);
  Fs->draw_it=&CadDrawIt;
  try {
    while (TRUE) {
      ch=GetKey(&sc);
      if (CadDoKey(ch,sc.u8[0])) goto cad_done;
    }
cad_done: //Don't goto out of try
  } catch
    PutExcept;
  SettingsPop;
  CadCleanUp;
  MenuPop;
}
