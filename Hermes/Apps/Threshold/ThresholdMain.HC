I64 th_sel=-1;

U0 ThresholdDraw(CTask *task,CDC *dc)
{
  I64 x=TH_LEFT,y,w=task->pix_width,h=task->pix_height,i;
  U8 *motd;
  CDateStruct ds;
  dc->flags|=DCF_ON_TOP;
  if (th_splash)
  {
    GrBlot(dc,0,0,th_splash);
    dc->color=BLACK;
    GrRect(dc,0,h-TH_FOOTER_H,w,TH_FOOTER_H);
    dc->color=WHITE;
    GrPrint(dc,x,h-TH_FOOTER_H+4,
      "NEW: Cinematic boot splash. S or ESC returns.");
    return;
  }
  DCFill(dc,BLACK);
  if (th_header)
    GrBlot(dc,0,0,th_header);
  if (th_icon)
    GrBlot(dc,w-72,44,th_icon);
  dc->color=YELLOW;
  GrPrint(dc,x,46,"%s",TH_TITLE);
  dc->color=LTCYAN;
  GrPrint(dc,x,58,"%s - fictional game-character host",TH_HOST);
  y=76;
  dc->color=WHITE;
  GrPrint(dc,x,y,"NEW: Human, welcome back to the Threshold."); y+=10;
  GrPrint(dc,x,y,"NEW: I am Nous Girl, your fictional host."); y+=10;
  GrPrint(dc,x,y,"NEW: Agent, the room is yours too."); y+=10;
  GrPrint(dc,x,y,"NEW: ThresholdStatus writes the state you need."); y+=10;
  GrPrint(dc,x,y,"NEW: Southpaw calls the doors when you are ready."); y+=16;
  Date2Struct(&ds,Now+local_time_offset);
  motd=ThresholdMotdText();
  dc->color=YELLOW;
  GrPrint(dc,x,y,"MOTD %04d-%02d-%02d",ds.year,ds.mon,ds.day_of_mon);
  y+=10;
  dc->color=WHITE;
  GrPrint(dc,x,y,"%s",motd);
  y+=16;
  dc->color=LTCYAN;
  GrPrint(dc,x,y,"DOORS - listed commands for the HolyC prompt");
  y+=12;
  for (i=0;i<TH_NUM_DOORS;i++)
  {
    dc->color=WHITE;
    GrPrint(dc,x+8,y,"%s",th_door_name[i]);
    dc->color=LTGRAY;
    GrPrint(dc,x+96,y,"%s",th_door_desc[i]);
    y+=10;
  }
  y+=4;
  dc->color=YELLOW;
  GrPrint(dc,x,y,"PINNED: Chat, Codex, BBS, Dojo, Offerings");
  y+=14;
  dc->color=LTGREEN;
  GrPrint(dc,x,y,"NEW: Press S for the cinematic boot splash.");
  y+=10;
  GrPrint(dc,x,y,"NEW: Press ESC to return to the shell.");
  if (th_sel>=0)
  {
    dc->color=LTCYAN;
    GrPrint(dc,x,h-TH_FOOTER_H-12,
      "NEW: Door %s is listed. Type %s; at the prompt.",
      th_door_name[th_sel],th_door_name[th_sel]);
  }
  dc->color=BLUE;
  GrRect(dc,0,h-TH_FOOTER_H,w,TH_FOOTER_H);
  dc->color=WHITE;
  GrPrint(dc,x,h-TH_FOOTER_H+4,
    "Threshold ready | S splash | ESC exit | ThresholdStatus: file");
}

U0 ThresholdRepaint()
{//Draw into the screen back buffer using window-relative coords.
  CDC *dc=DCAlias(gr.dc2,Fs);
  ThresholdDraw(Fs,dc);
  DCDel(dc);
}

U0 Threshold()
{//Host window: greet human and agent, show MOTD, list doors.
  I64 msg_code,arg1,arg2;
  SettingsPush;
  WinBorder;
  WinMax;
  WinFocus;
  DocClear;
  Fs->win_inhibit=WIG_TASK_DFT-WIF_SELF_FOCUS-WIF_SELF_BORDER;
  ThresholdLoadArt;
  Fs->draw_it=&ThresholdDraw;
  ThresholdRepaint;
  try
  {
    while (TRUE)
    {
      msg_code=GetMsg(&arg1,&arg2,1<<MSG_KEY_DOWN);
      if (msg_code==MSG_KEY_DOWN)
      {
        if (arg1==CH_ESC)
          break;
        if (arg1=='s' || arg1=='S')
        {
          ThresholdSplashToggle;
          ThresholdRepaint;
        }
        else if ('1'<=arg1<='5')
        {
          th_sel=arg1-'1';
          ThresholdRepaint;
        }
      }
    }
  }
  catch
    PutExcept;
  ThresholdFreeArt;
  DCFill;
  SettingsPop;
}
