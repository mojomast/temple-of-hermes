#ifndef DOJO_TASK_HC
#define DOJO_TASK_HC
#include "DojoPaint.HC"
CTask *dojo_tick_task=NULL;
I64 dojo_tick=0;
I64 dojo_demo=0;
U0 DojoTickTask(U8 *)
{
  while (TRUE) { dojo_tick++; Sleep(100); }
}
U0 DojoTask(U8 *)
{
  I64 sc; U8 key;
  U8 *p=DojoPath("UI/header-dojo-plate.GR");
  dojo_plate=GRRead(p); Free(p);
  p=DojoPath("Icons/64/teknium.GR");
  if (!FileFind(p)) { Free(p); p=DojoPath("Icons/32/teknium.GR"); }
  dojo_tek=GRRead(p); Free(p);
  DojoLoadScores();
  dojo_tick_task=Spawn(&DojoTickTask,NULL,"Dojo Tick");
  SettingsPush;
  DocClear;
  AutoComplete;
  WinBorder;
  LBts(&Fs->display_flags,DISPLAYf_SHOW);
  Fs->win_inhibit&=~WIF_SELF_FOCUS;
  WinMax;
  WinFocus;
  WinToTop;
  DocCursor;
  Fs->draw_it=&DojoDrawIt;
  if (dojo_demo)
  {
    try { DojoCheck(2); } catch PutExcept;
    try { DojoCheck(4); } catch PutExcept;
    DojoLoadScores();
  }
  F64 t0=tS;
  try
  {
    while (TRUE)
    {
      if (dojo_demo && tS-t0>15.0) break;
      if (ScanKey(&key,&sc))
      {
        if (key==CH_ESC||key==CH_CTRLQ||key==CH_SHIFT_ESC) break;
        if (key>='1'&&key<='4')
        {
          DojoCheck(key-'0');
          DojoLoadScores();
          DojoShowResult(key-'0');
        }
        else if (key=='p'||key=='P') DojoPlaque();
        else if (key=='r'||key=='R') { DojoLoadScores(); DojoReport(); }
      }
      Sleep(5);
    }
  }
  catch PutExcept;
  Fs->draw_it=NULL;
  if (TaskValidate(dojo_tick_task)) Kill(dojo_tick_task);
  SettingsPop;
  MenuPop;
  if (dojo_plate) { DCDel(dojo_plate); dojo_plate=NULL; }
  if (dojo_tek) { DCDel(dojo_tek); dojo_tek=NULL; }
}
U0 Dojo()
{
  DojoTask(NULL);
}
#endif
