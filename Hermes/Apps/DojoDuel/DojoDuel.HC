#ifndef DOJODUEL_MAIN_V8_HC
#define DOJODUEL_MAIN_V8_HC
#include "DuelDraw.HC"
#include "DuelInput.HC"
#include "DuelAgent.HC"
U0 DojoDuelRun(Bool agent=FALSE)
{
  I64 ch,sc;
  if (agent)
  {
    DojoDuelAgent(NULL);
    return;
  }
  DuelLoadAssets;
  DuelLoadBest;
  DuelSaveBest;
  duel_state=DUEL_TITLE;
  SettingsPush;
  DocClear;
  AutoComplete;
  WinBorder;
  WinMax;
  DocCursor;
  MenuPush(
  "File {"
  "  Abort(,CH_SHIFT_ESC);"
  "  Exit(,CH_ESC);"
  "}"
  "Play {"
  "  Restart(,'\n');"
  "}"
  );
  Fs->draw_it=&DuelDrawIt;
  try
  {
    while (TRUE)
    {
      DuelTick;
      if (ScanKey(&ch,&sc))
      {
        if (ch==CH_ESC || ch==CH_SHIFT_ESC || ch==CH_CTRLQ) break;
        DuelHandleKey(ch);
      }
      Refresh;
      Sleep(4);
    }
  }
  catch PutExcept;
  Fs->draw_it=NULL;
  SettingsPop;
  MenuPop;
  DuelFreeAssets;
}
U0 DojoDuel(Bool agent=FALSE)
{
  DojoDuelRun(agent);
}
#endif
