#ifndef HERMES_OFFERINGS_UI_HC
#define HERMES_OFFERINGS_UI_HC

U0 OfferingsSetStatus(COfferUI *s,U8 *st)
{
  if (s->status)
    Free(s->status);
  if (st)
    s->status=StrNew(st);
  else
    s->status=StrNew("");
}

U0 OfferingsSetStatusTake(COfferUI *s,U8 *st)
{
  if (s->status)
    Free(s->status);
  if (st)
    s->status=st;
  else
    s->status=StrNew("");
}

U0 OfferingsSelect(COfferUI *s,I64 idx)
{
  COfferItem *it;
  if (idx<0)
    idx=0;
  if (idx>=offer_count)
    idx=offer_count-1;
  s->selected=idx;
  it=&offer_items[idx];
  if (it->price>0)
    OfferingsSetStatusTake(s,MStrPrint("%s - %s - %d spoons",
      it->title,it->blurb,it->price));
  else
    OfferingsSetStatusTake(s,MStrPrint("%s - %s - free",it->title,it->blurb));
}

U0 OfferingsLoadSnippet(COfferUI *s,COfferItem *it)
{
  U8 *src;
  I64 size=0;
  if (s->snippet_text)
  {
    Free(s->snippet_text);
    s->snippet_text=NULL;
  }
  if (s->snippet_name)
  {
    Free(s->snippet_name);
    s->snippet_name=NULL;
  }
  src=OfferSourcePath(it);
  if (!src)
    return;
  s->snippet_text=FileRead(src,&size);
  s->snippet_name=StrNew(it->title);
  Free(src);
}

U0 OfferingsPreview(COfferUI *s)
{
  COfferItem *it=&offer_items[s->selected];
  U8 *home,*dest;
  Bool ok=FALSE;
  try
  {
  ok=OfferInstall(it);
  if (s->spoons>=it->price)
    s->spoons-=it->price;
  else
    OfferingsSetStatus(s,"Don Piedro waves the spoon fee. For Hermes!");
  if (it->cat==OFFER_WALL)
  {
    if (s->wall)
    {
      DCDel(s->wall);
      s->wall=NULL;
    }
    home=OfferHome();
    dest=MStrPrint("%s%s",home,it->dest);
    if (IsFile(dest))
      s->wall=GRRead(dest);
    Free(dest);
    Free(home);
    if (!s->wall)
      s->wall=OfferLoadWall(it->src);
    s->mode=OFFER_MODE_WALL;
    if (!ok)
      OfferingsSetStatus(s,"Wallpaper source missing; showing what is here.");
    else
      OfferingsSetStatusTake(s,MStrPrint("Installed %s.  Esc returns to the shop.",it->title));
  }
  else if (it->cat==OFFER_SNIP)
  {
    OfferingsLoadSnippet(s,it);
    s->mode=OFFER_MODE_SNIP;
    if (!ok)
      OfferingsSetStatus(s,"Snippet source missing; preview is empty.");
    else
      OfferingsSetStatusTake(s,MStrPrint("Installed %s.  Esc returns to the shop.",it->title));
  }
  else
  {
    s->mode=OFFER_MODE_PAL;
    if (!ok)
      OfferingsSetStatus(s,"Palette card source missing; showing the temple sixteen.");
    else
      OfferingsSetStatusTake(s,MStrPrint("Installed %s.  Esc returns to the shop.",it->title));
  }
  }
  catch
  {
    PutExcept;
    s->mode=OFFER_MODE_SHOP;
    OfferingsSetStatus(s,"Preview failed; the shop is still open.");
  }
}

U0 OfferingsBack(COfferUI *s)
{
  if (s->wall)
  {
    DCDel(s->wall);
    s->wall=NULL;
  }
  if (s->snippet_text)
  {
    Free(s->snippet_text);
    s->snippet_text=NULL;
  }
  if (s->snippet_name)
  {
    Free(s->snippet_name);
    s->snippet_name=NULL;
  }
  s->mode=OFFER_MODE_SHOP;
  OfferingsSetStatus(s,"Pick an offering.  Enter previews and installs.");
}

U0 OfferingsTask(U8 *data)
{
  COfferUI *s;
  I64 msg_code,arg1,arg2,running=TRUE;
  data=0;
  OfferingsInit;
  s=CAlloc(sizeof(COfferUI));
  s->selected=0;
  s->mode=OFFER_MODE_SHOP;
  s->spoons=12;
  s->plate=OfferLoadPlate();
  s->piedro=OfferLoadPiedro(32);
  s->status=StrNew("Pick an offering.  Enter previews and installs.");
  Fs->user_data=s(I64);
  DocTermNew;
  SettingsPush;
  AutoComplete(FALSE);
  StrCpy(Fs->task_title,"Offerings");
  Fs->title_src=TTS_LOCKED_CONST;
  Fs->win_inhibit=WIG_USER_TASK_DFT;
  Fs->draw_it=&OfferingsDraw;
  WinBorder(TRUE);
  WinHorz(0,80);
  WinVert(0,60);
  LBts(&Fs->display_flags,DISPLAYf_SHOW);
  WinToTop;
  WinFocus;
  DocClear;
  Refresh;
  Sleep(500);
  WinToTop;
  WinFocus;
  Refresh;
  try
  {
    while (running)
    {
      msg_code=GetMsg(&arg1,&arg2,1<<MSG_KEY_DOWN);
      if (msg_code==MSG_KEY_DOWN)
      {
        if (arg1==CH_ESC || arg1==CH_SHIFT_ESC)
        {
          if (s->mode!=OFFER_MODE_SHOP)
            OfferingsBack(s);
          else
            running=FALSE;
        }
        else if (s->mode==OFFER_MODE_SHOP)
        {
          if (arg2.u8[0]==SC_CURSOR_UP)
          {
            if (s->selected>=4)
              OfferingsSelect(s,s->selected-4);
          }
          else if (arg2.u8[0]==SC_CURSOR_DOWN)
          {
            if (s->selected+4<offer_count)
              OfferingsSelect(s,s->selected+4);
          }
          else if (arg2.u8[0]==SC_CURSOR_LEFT)
          {
            if (s->selected>0)
              OfferingsSelect(s,s->selected-1);
          }
          else if (arg2.u8[0]==SC_CURSOR_RIGHT)
          {
            if (s->selected<offer_count-1)
              OfferingsSelect(s,s->selected+1);
          }
          else if (arg1==CH_CTRLM || arg1=='\n')
            OfferingsPreview(s);
          else if (arg1=='l' || arg1=='L')
          {
            OfferingsList;
            OfferingsSetStatus(s,"Catalog written to C:/Tmp/Offerings/Results/list.json");
          }
          else if (arg1=='g' || arg1=='G')
          {
            OfferingsGet(offer_items[s->selected].id);
            OfferingsSetStatusTake(s,MStrPrint("Get written for %s",offer_items[s->selected].id));
          }
          else if (arg1=='i' || arg1=='I')
          {
            if (OfferInstall(&offer_items[s->selected]))
              OfferingsSetStatusTake(s,MStrPrint("Installed %s",offer_items[s->selected].title));
            else
              OfferingsSetStatus(s,"Source missing; nothing installed.");
          }
          else if (arg1=='q' || arg1=='Q')
            running=FALSE;
        }
        else
        {
          if (arg1=='i' || arg1=='I')
          {
            if (OfferInstall(&offer_items[s->selected]))
              OfferingsSetStatusTake(s,MStrPrint("Installed %s",offer_items[s->selected].title));
            else
              OfferingsSetStatus(s,"Source missing; nothing installed.");
          }
        }
        Refresh;
        Yield;
      }
    }
  }
  catch
    PutExcept;
  GetMsg(,,1<<MSG_KEY_UP);
  if (s->plate)
    DCDel(s->plate);
  if (s->piedro)
    DCDel(s->piedro);
  if (s->wall)
    DCDel(s->wall);
  if (s->snippet_text)
    Free(s->snippet_text);
  if (s->snippet_name)
    Free(s->snippet_name);
  if (s->status)
    Free(s->status);
  Free(s);
  Fs->draw_it=NULL;
  Fs->user_data=0;
  SettingsPop;
  DocClear;
  Refresh;
}

U0 OfferingsRun()
{//Open Don Piedro's shop in its own window.
  Spawn(&OfferingsTask,NULL,"Offerings");
}

U0 OfferingsOpen()
{
  OfferingsRun;
}

#endif
