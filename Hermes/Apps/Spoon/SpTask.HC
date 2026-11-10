#ifndef SP_TASK_HC
#define SP_TASK_HC

U0 SpoonTask(U8 *data)
{
  CSpoon *s;
  I64 arg1,arg2,running=TRUE;
  F64 dt;
  data=0;
  s=CAlloc(sizeof(CSpoon));
  SpInit(s,FALSE);
  Fs->user_data=s(I64);
  SpWindowSetup;
  try
  {
    while (running)
    {
      switch (ScanMsg(&arg1,&arg2,1<<MSG_KEY_DOWN))
      {
      case MSG_KEY_DOWN:
        if (arg1==CH_ESC || arg1==CH_SHIFT_ESC)
          running=FALSE;
        else if (!s->started)
        {
          if (arg1=='\n' || arg1==' ')
            s->started=TRUE;
        }
        else if (s->over)
        {
          if (arg1=='\n')
            SpReset(s);
        }
        break;
      }
      dt=0.015;
      s->t=s->t+dt;
      if (s->started && !s->over)
      {
        if (Bt(&kbd.down_bitmap,SC_CURSOR_LEFT))
          s->spoon_x=s->spoon_x-360.0*dt;
        if (Bt(&kbd.down_bitmap,SC_CURSOR_RIGHT))
          s->spoon_x=s->spoon_x+360.0*dt;
        s->spoon_x=Clamp(s->spoon_x,SP_SPOON_MIN,SP_SPOON_MAX);
        SpMaybeToss(s);
        SpStep(s,dt);
        SpCheckEnd(s);
      }
      Refresh;
      Sleep(15);
    }
  }
  catch
    PutExcept;
  GetMsg(,,1<<MSG_KEY_UP);
  Fs->draw_it=NULL;
  Fs->user_data=0;
  SpFree(s);
  MenuPop;
  SettingsPop;
  DocClear;
  Refresh;
}

#endif
