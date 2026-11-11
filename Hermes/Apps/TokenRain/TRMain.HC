U0 TRSong(I64)
{
  Fs->task_end_cb=&SndTaskEndCB;
  MusicSettingsRst;
  while (TRUE)
  {
    Play("4AB5C");
    Play("4AB5C");
  }
}

U0 TRAnimate(I64)
{
  F64 t0=tS,dt;
  while (TRUE)
  {
    dt=tS-t0;
    if (dt<0)
      dt=0;
    if (dt>0.1)
      dt=0.1;
    t0=tS;
    if (tr_state==1)
      TRUpdate(dt,tr_kl,tr_kr);
    if (tr_flash>0)
      tr_flash-=dt;
    Refresh;
    Sleep(10);
  }
}

U0 TokenRain(Bool agent=FALSE)
{
  I64 arg1,arg2;
  SettingsPush;
  Fs->text_attr=WHITE<<4+BLUE;
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
    "  Start(,'\n');"
    "  Left(,,SC_CURSOR_LEFT);"
    "  Right(,,SC_CURSOR_RIGHT);"
    "}"
  );
  TRLoadArt;
  TRLoadHigh;
  if (agent)
    TRAgentSim;
  else
  {
    TRReset(FALSE);
    tr_state=0;
  }
  Fs->song_task=Spawn(&TRSong,NULL,"Song",,Fs);
  Fs->animate_task=Spawn(&TRAnimate,NULL,"Animate",,Fs);
  Fs->draw_it=&TRDraw;
  try
  {
    while (TRUE)
    {
      switch (GetMsg(&arg1,&arg2,1<<MSG_KEY_DOWN+1<<MSG_KEY_UP))
      {
      case MSG_KEY_DOWN:
        if (!arg1)
        {
          switch (arg2.u8[0])
          {
          case SC_CURSOR_LEFT:
            tr_kl=TRUE;
            break;
          case SC_CURSOR_RIGHT:
            tr_kr=TRUE;
            break;
          }
        }
        else
          switch (arg1)
          {
          case 'a':
          case 'A':
            tr_kl=TRUE;
            break;
          case 'd':
          case 'D':
            tr_kr=TRUE;
            break;
          case '\n':
            if (tr_state==0 || tr_state==2)
            {
              TRReset(FALSE);
              tr_state=1;
            }
            else if (tr_state==3)
              goto tr_done;
            break;
          case CH_SHIFT_ESC:
          case CH_ESC:
            if (tr_state==1)
              tr_state=0;
            else
              goto tr_done;
            break;
          }
        break;
      case MSG_KEY_UP:
        if (!arg1)
        {
          switch (arg2.u8[0])
          {
          case SC_CURSOR_LEFT:
            tr_kl=FALSE;
            break;
          case SC_CURSOR_RIGHT:
            tr_kr=FALSE;
            break;
          }
        }
        else
          switch (arg1)
          {
          case 'a':
          case 'A':
            tr_kl=FALSE;
            break;
          case 'd':
          case 'D':
            tr_kr=FALSE;
            break;
          }
        break;
      }
    }
tr_done:
    GetMsg(,,1<<MSG_KEY_UP);
  }
  catch
    PutExcept;
  SettingsPop;
  TRFreeArt;
  MenuPop;
}

U0 TokenRainStart()
{
  TokenRain(FALSE);
}

U0 TokenRainAgentUI()
{
  TokenRain(TRUE);
}
