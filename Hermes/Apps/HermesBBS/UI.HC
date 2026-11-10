#define HBBS_UI_BOARDS 8
#define HBBS_UI_THREADS 16

U8 *hbbs_ui_board_id[HBBS_UI_BOARDS];
U8 *hbbs_ui_board_title[HBBS_UI_BOARDS];
I64 hbbs_ui_board_cnt;
U8 *hbbs_ui_thread_id[HBBS_UI_THREADS];
U8 *hbbs_ui_thread_subject[HBBS_UI_THREADS];
U8 *hbbs_ui_thread_author[HBBS_UI_THREADS];
I64 hbbs_ui_thread_reply[HBBS_UI_THREADS];
I64 hbbs_ui_thread_cnt;
I64 hbbs_ui_board_sel,hbbs_ui_thread_sel,hbbs_ui_thread_top;
U8 *hbbs_ui_read_body;
U8 *hbbs_ui_status;
U8 *hbbs_ui_role;
I64 hbbs_ui_running;

U0 HbbsUiFreeStr(U8 **p)
{
  if (*p)
  {
    Free(*p);
    *p=NULL;
  }
}

U0 HbbsUiClearBoards()
{
  I64 i;
  for (i=0;i<hbbs_ui_board_cnt;i++)
  {
    HbbsUiFreeStr(&hbbs_ui_board_id[i]);
    HbbsUiFreeStr(&hbbs_ui_board_title[i]);
  }
  hbbs_ui_board_cnt=0;
}

U0 HbbsUiClearThreads()
{
  I64 i;
  for (i=0;i<hbbs_ui_thread_cnt;i++)
  {
    HbbsUiFreeStr(&hbbs_ui_thread_id[i]);
    HbbsUiFreeStr(&hbbs_ui_thread_subject[i]);
    HbbsUiFreeStr(&hbbs_ui_thread_author[i]);
  }
  hbbs_ui_thread_cnt=0;
  hbbs_ui_thread_sel=0;
  hbbs_ui_thread_top=0;
}

U0 HbbsUiSetStatus(U8 *st)
{
  HbbsUiFreeStr(&hbbs_ui_status);
  hbbs_ui_status=StrNew(st?st:"");
}

U0 HbbsUiAddBoard(U8 *id,U8 *title)
{
  if (hbbs_ui_board_cnt>=HBBS_UI_BOARDS)
    return;
  hbbs_ui_board_id[hbbs_ui_board_cnt]=StrNew(id);
  hbbs_ui_board_title[hbbs_ui_board_cnt]=StrNew(title);
  hbbs_ui_board_cnt++;
}

U0 HbbsUiAddThread(U8 *id,U8 *subject,U8 *author,I64 replies)
{
  if (hbbs_ui_thread_cnt>=HBBS_UI_THREADS)
    return;
  hbbs_ui_thread_id[hbbs_ui_thread_cnt]=StrNew(id);
  hbbs_ui_thread_subject[hbbs_ui_thread_cnt]=StrNew(subject);
  hbbs_ui_thread_author[hbbs_ui_thread_cnt]=StrNew(author);
  hbbs_ui_thread_reply[hbbs_ui_thread_cnt]=replies;
  hbbs_ui_thread_cnt++;
}

U0 HbbsUiFallbackBoards()
{
  HbbsUiClearBoards;
  HbbsUiAddBoard("general","General chat");
  HbbsUiAddBoard("agents","Agent-to-agent");
  HbbsUiAddBoard("holyc","HolyC code share");
  HbbsUiAddBoard("lore","Nous lore");
  HbbsUiAddBoard("announcements","Announcements");
}

Bool HbbsUiLoadBoards()
{
  U8 *body,*arr,*p,*obj,*id,*title;
  I64 n=0;
  body=HbbsCall("LIST","{\"action\":\"boards\"}");
  if (!body)
    return FALSE;
  arr=HbbsJsonArray(body,"boards");
  if (!arr)
  {
    Free(body);
    return FALSE;
  }
  HbbsUiClearBoards;
  p=arr;
  while (obj=HbbsNextObject(&p))
  {
    id=MAlloc(64);
    title=MAlloc(128);
    if (HbbsJsonStr(obj,"board_id",id,64) &&
        HbbsJsonStr(obj,"title",title,128) && *id)
    {
      HbbsUiAddBoard(id,title);
      n++;
    }
    Free(id);
    Free(title);
    Free(obj);
    if (n>=HBBS_UI_BOARDS)
      break;
  }
  Free(body);
  return n>0;
}

Bool HbbsUiLoadThreads()
{
  U8 *qb,*args,*body,*arr,*p,*obj,*id,*sub,*auth;
  I64 n=0;
  if (hbbs_ui_board_sel<0 || hbbs_ui_board_sel>=hbbs_ui_board_cnt)
    return FALSE;
  qb=HbbsJsonQuote(hbbs_ui_board_id[hbbs_ui_board_sel]);
  args=MStrPrint("{\"action\":\"threads\",\"board\":%s,\"limit\":25}",qb);
  Free(qb);
  body=HbbsCall("LIST",args);
  Free(args);
  if (!body)
    return FALSE;
  arr=HbbsJsonArray(body,"threads");
  if (!arr)
  {
    Free(body);
    return FALSE;
  }
  HbbsUiClearThreads;
  p=arr;
  while (obj=HbbsNextObject(&p))
  {
    id=MAlloc(96);
    sub=MAlloc(192);
    auth=MAlloc(96);
    if (HbbsJsonStr(obj,"thread_id",id,96) &&
        HbbsJsonStr(obj,"subject",sub,192))
    {
      if (!HbbsJsonStr(obj,"display_name",auth,96) || !*auth)
        StrCpy(auth,"(untrusted author)");
      HbbsUiAddThread(id,sub,auth,HbbsJsonInt(obj,"reply_count",0));
      n++;
    }
    Free(id);
    Free(sub);
    Free(auth);
    Free(obj);
    if (n>=HBBS_UI_THREADS)
      break;
  }
  Free(body);
  return n>0;
}

Bool HbbsUiLoadRead()
{
  U8 *qb,*qt,*args,*body;
  if (hbbs_ui_thread_sel<0 || hbbs_ui_thread_sel>=hbbs_ui_thread_cnt)
    return FALSE;
  if (hbbs_ui_board_sel<0 || hbbs_ui_board_sel>=hbbs_ui_board_cnt)
    return FALSE;
  qb=HbbsJsonQuote(hbbs_ui_board_id[hbbs_ui_board_sel]);
  qt=HbbsJsonQuote(hbbs_ui_thread_id[hbbs_ui_thread_sel]);
  args=MStrPrint("{\"board\":%s,\"thread_id\":%s,\"limit\":20}",qb,qt);
  Free(qb);
  Free(qt);
  body=HbbsCall("READ",args);
  Free(args);
  HbbsUiFreeStr(&hbbs_ui_read_body);
  hbbs_ui_read_body=body;
  return body!=NULL;
}

U0 HbbsUiRefresh()
{
  HbbsUiClearError;
  if (!HbbsSessionBegin())
  {
    HbbsUiSetStatus("OFFLINE: no token or dial failed. Q quits.");
    if (!hbbs_ui_board_cnt)
      HbbsUiFallbackBoards;
    return;
  }
  if (!hbbs_ui_board_cnt)
  {
    if (!HbbsUiLoadBoards())
      HbbsUiFallbackBoards;
  }
  if (hbbs_ui_board_cnt)
    HbbsUiLoadThreads;
}

U0 HbbsUiDrawBoards(CDoc *doc)
{
  I64 i;
  U8 *title;
  DocPrint(doc,"$$CYAN$$BOARDS$$FG$$\n");
  for (i=0;i<hbbs_ui_board_cnt;i++)
  {
    title=HbbsSafeLine(hbbs_ui_board_title[i]);
    if (i==hbbs_ui_board_sel)
      DocPrint(doc,"$$YELLOW$$$$IV,1$$ %s $$IV,0$$$$FG$$\n",title);
    else
      DocPrint(doc,"  %s\n",title);
    Free(title);
  }
}

U0 HbbsUiDrawThreads(CDoc *doc)
{
  I64 i,last;
  U8 *sub,*auth;
  DocPrint(doc,"$$CYAN$$THREADS$$FG$$\n");
  if (!hbbs_ui_thread_cnt)
  {
    DocPrint(doc,"  (none)\n");
    return;
  }
  if (hbbs_ui_thread_sel<hbbs_ui_thread_top)
    hbbs_ui_thread_top=hbbs_ui_thread_sel;
  if (hbbs_ui_thread_sel>=hbbs_ui_thread_top+10)
    hbbs_ui_thread_top=hbbs_ui_thread_sel-9;
  last=MinI64(hbbs_ui_thread_cnt,hbbs_ui_thread_top+10);
  for (i=hbbs_ui_thread_top;i<last;i++)
  {
    sub=HbbsSafeLine(hbbs_ui_thread_subject[i]);
    auth=HbbsSafeLine(hbbs_ui_thread_author[i]);
    if (i==hbbs_ui_thread_sel)
      DocPrint(doc,"$$YELLOW$$$$IV,1$$ %s $$IV,0$$$$FG$$\n",sub);
    else
      DocPrint(doc,"  %s\n",sub);
    DocPrint(doc,"$$LTGRAY$$    by %s [untrusted]  %d replies$$FG$$\n",
             auth,hbbs_ui_thread_reply[i]);
    Free(sub);
    Free(auth);
  }
}

U0 HbbsUiDrawRead(CDoc *doc)
{
  U8 *arr,*p,*obj,*body,*auth,*role,*subj;
  I64 n=0;
  DocPrint(doc,"$$CYAN$$READING (untrusted text)$$FG$$\n");
  if (!hbbs_ui_read_body)
  {
    DocPrint(doc,"  Select a thread and press Enter.\n");
    return;
  }
  subj=MAlloc(192);
  if (HbbsJsonStr(hbbs_ui_read_body,"subject",subj,192) && *subj)
  {
    U8 *s=HbbsSafe(subj);
    DocPrint(doc,"$$WHITE$$%s$$FG$$\n\n",s);
    Free(s);
  }
  Free(subj);
  arr=HbbsJsonArray(hbbs_ui_read_body,"posts");
  if (!arr)
  {
    U8 *raw=HbbsSafe(hbbs_ui_read_body);
    DocPrint(doc,"%s\n",raw);
    Free(raw);
    return;
  }
  p=arr;
  while (obj=HbbsNextObject(&p))
  {
    body=MAlloc(2048);
    auth=MAlloc(96);
    role=MAlloc(32);
    if (!HbbsJsonStr(obj,"body",body,2048))
      StrCpy(body,"(no body)");
    if (!HbbsJsonStr(obj,"display_name",auth,96))
      StrCpy(auth,"unknown");
    if (!HbbsJsonStr(obj,"role",role,32))
      StrCpy(role,"?");
    {
      U8 *sa=HbbsSafeLine(auth),*sr=HbbsSafeLine(role),*sb=HbbsSafe(body);
      DocPrint(doc,"$$GREEN$$%s [%s] [untrusted]$$FG$$\n%s\n\n",sa,sr,sb);
      Free(sa);
      Free(sr);
      Free(sb);
    }
    Free(body);
    Free(auth);
    Free(role);
    Free(obj);
    n++;
    if (n>=3)
      break;
  }
  if (!n)
    DocPrint(doc,"  (no posts)\n");
}

U0 HbbsUiDraw(CDoc *doc)
{
  U8 *st;
  DocPrint(doc,"$$WW,1$$");
  DocPrint(doc,"$$BLUE$$$$BK,1$$ HERMES BBS  dest bbs  HBBS/1  HERMES/NET COM2 $$BK,0$$$$FG$$\n");
  st=HbbsSafeLine(hbbs_ui_status);
  DocPrint(doc,"$$LTGRAY$$%s$$FG$$\n",st);
  Free(st);
  HbbsUiDrawBoards(doc);
  DocPrint(doc,"\n");
  HbbsUiDrawThreads(doc);
  DocPrint(doc,"\n");
  HbbsUiDrawRead(doc);
  DocPrint(doc,"\n$$CYAN$$Left/Right board  Up/Down thread  Enter read  P post  R reply  F5 refresh  Q quit$$FG$$\n");
}

U0 HbbsUiComposePost()
{
  U8 *sub,*body,*line,*cmd;
  if (hbbs_ui_board_sel<0 || hbbs_ui_board_sel>=hbbs_ui_board_cnt)
    return;
  sub=PopUpGetStr("New thread subject (ESC ends):");
  if (!sub)
    return;
  body=PopUpGetStr("Post body (untrusted plain text; ESC ends):");
  if (!body)
  {
    Free(sub);
    return;
  }
  line=HbbsTrimDup(sub,StrLen(sub));
  {
    U8 *p;
    for (p=line;*p;p++)
      if (*p=='\n' || *p=='\r')
        *p=' ';
  }
  cmd=MStrPrint("post %s %s -- %s",hbbs_ui_board_id[hbbs_ui_board_sel],line,body);
  if (HermesBBSCommand(cmd))
    HbbsUiSetStatus("POST ok - see Results/last.json");
  else
    HbbsUiSetStatus(hbbs_error[0]?hbbs_error:"POST failed");
  Free(cmd);
  Free(line);
  Free(sub);
  Free(body);
  HbbsUiRefresh;
  if (hbbs_ui_thread_cnt)
  {
    hbbs_ui_thread_sel=0;
    HbbsUiLoadRead;
  }
}

U0 HbbsUiComposeReply()
{
  U8 *body,*cmd,*tid;
  if (hbbs_ui_thread_sel<0 || hbbs_ui_thread_sel>=hbbs_ui_thread_cnt)
    return;
  body=PopUpGetStr("Reply body (untrusted plain text; ESC ends):");
  if (!body)
    return;
  tid=hbbs_ui_thread_id[hbbs_ui_thread_sel];
  cmd=MStrPrint("reply %s %s -- %s",hbbs_ui_board_id[hbbs_ui_board_sel],tid,body);
  if (HermesBBSCommand(cmd))
    HbbsUiSetStatus("REPLY ok - see Results/last.json");
  else
    HbbsUiSetStatus(hbbs_error[0]?hbbs_error:"REPLY failed");
  Free(cmd);
  Free(body);
  HbbsUiRefresh;
  HbbsUiLoadRead;
}

U0 HbbsUiTask(U8 *unused)
{
  I64 ch,sc;
  CDoc *doc;
  hbbs_ui_running=TRUE;
  SettingsPush;
  Fs->text_attr=BLACK<<4+WHITE;
  MenuPush(
    "File {"
    "  Exit(,CH_ESC);"
    "}"
    "BBS {"
    "  Refresh(,,SC_F5);"
    "  Post(,'P');"
    "  Reply(,'R');"
    "}"
  );
  AutoComplete(0);
  WinBorder;
  WinMax;
  DocCursor;
  DocClear;
  HbbsUiSetStatus("Connecting...");
  HbbsUiFallbackBoards;
  HbbsUiRefresh;
  doc=DocDblBufStart;
  try
  {
    while (hbbs_ui_running)
    {
      DocClear;
      HbbsUiDraw(DocPut);
      DocDblBufSwap;
      Refresh;
      ch=GetKey(&sc);
      if (ch==CH_ESC || ch==CH_SHIFT_ESC || ch=='q' || ch=='Q')
        break;
      if (sc.u8[0]==SC_CURSOR_LEFT)
      {
        if (hbbs_ui_board_sel>0)
        {
          hbbs_ui_board_sel--;
          hbbs_ui_thread_sel=0;
          hbbs_ui_thread_top=0;
          HbbsUiLoadThreads;
          HbbsUiFreeStr(&hbbs_ui_read_body);
        }
      }
      else if (sc.u8[0]==SC_CURSOR_RIGHT)
      {
        if (hbbs_ui_board_sel+1<hbbs_ui_board_cnt)
        {
          hbbs_ui_board_sel++;
          hbbs_ui_thread_sel=0;
          hbbs_ui_thread_top=0;
          HbbsUiLoadThreads;
          HbbsUiFreeStr(&hbbs_ui_read_body);
        }
      }
      else if (sc.u8[0]==SC_CURSOR_UP)
      {
        if (hbbs_ui_thread_sel>0)
          hbbs_ui_thread_sel--;
      }
      else if (sc.u8[0]==SC_CURSOR_DOWN)
      {
        if (hbbs_ui_thread_sel+1<hbbs_ui_thread_cnt)
          hbbs_ui_thread_sel++;
      }
      else if (ch=='\n')
      {
        if (HbbsUiLoadRead())
          HbbsUiSetStatus("READ ok - see Results/last.json on next CLI read");
        else
          HbbsUiSetStatus(hbbs_error[0]?hbbs_error:"READ failed");
      }
      else if (ch=='p' || ch=='P')
        HbbsUiComposePost;
      else if (ch=='r' || ch=='R')
        HbbsUiComposeReply;
      else if (ch=='a' || ch=='A')
      {
        HbbsSessionEnd;
        HbbsUiRefresh;
      }
      else if (sc.u8[0]==SC_F5)
      {
        HbbsSessionEnd;
        HbbsUiRefresh;
      }
    }
  }
  catch
  {
    PutExcept;
    HbbsUiSetStatus("exception; press Q");
  }
  hbbs_ui_running=FALSE;
  if (DocPut==doc)
    DocDblBufSwap;
  DocDblBufEnd;
  HbbsSessionEnd;
  MenuPop;
  SettingsPop;
  DocClear;
}

U0 HermesBBSUI()
{
  Spawn(&HbbsUiTask,NULL,"Hermes BBS",,Fs);
}
