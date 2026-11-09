// COM1 RPC server. Runs as a hidden background task.

#define HERMES_LINE_MAX	256

U8 hermes_line[HERMES_LINE_MAX];
I64 hermes_line_n=0;

U8 *HermesEval(U8 *src)
{
  CDoc *cap,*old;
  U8 *st,*esc,*out;
  I64 err=FALSE;
  if (!src) src="";
  cap=DocNew;
  old=Fs->put_doc;
  Fs->put_doc=cap;
  try
  {
    ExePrint("%s",src);
  }
  catch
  {
    Fs->catch_except=TRUE;
    err=TRUE;
    try
    {
      PutExcept;
    }
    catch
      Fs->catch_except=TRUE;
  }
  Fs->put_doc=old;
  st=HermesDocPlain(cap);
  if (!st) st=StrNew("");
  if (err || StrIMatch("\nErr",st) ||
      !StrNCmp(st,"Err",3) || StrIMatch("Exception",st))
  {
    HermesEventPush("compile_error",st);
    err=TRUE;
  }
  esc=HermesEsc(st);
  out=MStrPrint("{\"ok\":%d,\"text\":\"%s\"}",!err,esc);
  Free(st);
  Free(esc);
  DocDel(cap);
  return out;
}

CTask *HermesParseTask(U8 *s)
{
  CTask *task;
  I64 addr;
  if (!s) return NULL;
  while (*s==' ' || *s=='\t' || *s=='\n' || *s=='\r') s++;
  if (*s=='0' && (s[1]=='x' || s[1]=='X'))
  {
    addr=Str2I64(s);
    task=addr(CTask *);
    if (TaskValidate(task))
      return task;
  }
  if (*s)
    return FindTaskByTitle(s);
  return NULL;
}

U8 *HermesMouseJSON()
{
  return MStrPrint(
    "{\"x\":%d,\"y\":%d,\"z\":%d,\"lb\":%d,\"rb\":%d,"
    "\"agent_x\":%d,\"agent_y\":%d,\"mode\":\"%s\"}",
    ms.pos.x,ms.pos.y,ms.pos.z,ms.lb,ms.rb,
    hermes_agent_mx,hermes_agent_my,HermesModeName);
}

U8 *HermesIdleJSON()
{
  return MStrPrint(
    "{\"t\":%7.3f,\"mode\":\"%s\",\"prompt\":%d,"
    "\"evt_pending\":%d,\"ready\":%d}",
    tS,HermesModeName,hermes_prompt_armed,
    hermes_evt_head!=hermes_evt_tail,hermes_ready);
}

U8 *HermesHelpJSON()
{
  return StrNew(
    "{\"ops\":[\"ping\",\"eval\",\"tasks\",\"focus\",\"mouse\","
    "\"text\",\"mode\",\"clip_get\",\"clip_set\",\"list\",\"pull\","
    "\"push\",\"events\",\"idle\",\"help\"],"
    "\"name\":\"" HERMES_NAME "\",\"version\":\"" HERMES_VERSION "\"}");
}

U0 HermesHandle(I64 id,U8 *op,U8 *payload,I64 len)
{
  U8 *res=NULL,*path,tmp[64];
  CTask *task;
  I64 mode,size,wrote,i,x,y;
  U8 *data;
  if (!op) op="";
  if (!payload) payload="";

  if (!StrICmp(op,"ping") || !StrICmp(op,"help"))
  {
    if (!StrICmp(op,"help"))
      res=HermesHelpJSON;
    else
    {
      StrPrint(tmp,"{\"pong\":1,\"t\":%7.3f,\"mode\":\"%s\",\"version\":\"%s\"}",
               tS,HermesModeName,HERMES_VERSION);
      res=StrNew(tmp);
    }
    HermesReply(id,res);
    Free(res);
  }
  else if (!StrICmp(op,"eval"))
  {
    res=HermesEval(payload);
    HermesReply(id,res);
    Free(res);
  }
  else if (!StrICmp(op,"tasks"))
  {
    res=HermesTasksJSON;
    HermesReply(id,res);
    Free(res);
  }
  else if (!StrICmp(op,"focus"))
  {
    if (len>0 && *payload)
    {
      task=HermesParseTask(payload);
      if (task)
      {
        WinToTop(task);
        WinZBufUpdate;
      }
      else
      {
        HermesReplyErr(id,"no_task");
        return;
      }
    }
    res=HermesTasksJSON;
    HermesReply(id,res);
    Free(res);
  }
  else if (!StrICmp(op,"mouse"))
  {
    if (len>0 && *payload)
    {
      x=Str2I64(payload);
      i=0;
      while (payload[i] && payload[i]!=',') i++;
      if (payload[i]==',')
      {
        y=Str2I64(payload+i+1);
        hermes_agent_mx=ClampI64(x,0,GR_WIDTH-1);
        hermes_agent_my=ClampI64(y,0,GR_HEIGHT-1);
        if (hermes_mode==HERMES_MODE_AGENT)
          MsSet(hermes_agent_mx,hermes_agent_my);
      }
    }
    res=HermesMouseJSON;
    HermesReply(id,res);
    Free(res);
  }
  else if (!StrICmp(op,"text"))
  {
    if (StrIMatch("all",payload))
      res=HermesTextAll;
    else
      res=HermesTextFocus;
    HermesReply(id,res);
    Free(res);
  }
  else if (!StrICmp(op,"mode"))
  {
    mode=HermesModeFromName(payload);
    if (mode<0)
    {
      HermesReplyErr(id,"bad_mode");
      return;
    }
    HermesSetMode(mode);
    res=MStrPrint("{\"mode\":\"%s\"}",HermesModeName);
    HermesReply(id,res);
    Free(res);
  }
  else if (!StrICmp(op,"clip_get"))
  {
    res=HermesClipGet;
    HermesReply(id,res);
    Free(res);
  }
  else if (!StrICmp(op,"clip_set"))
  {
    HermesClipSet(payload);
    res=HermesClipGet;
    HermesReply(id,res);
    Free(res);
  }
  else if (!StrICmp(op,"list"))
  {
    res=HermesListDir(payload);
    HermesReply(id,res);
    Free(res);
  }
  else if (!StrICmp(op,"pull"))
  {
    path=payload;
    size=0;
    data=FileRead(path,&size);
    if (!data)
    {
      HermesReplyErr(id,"pull_read");
      return;
    }
    if (size<0 || size>HERMES_MAX_PAYLOAD)
    {
      Free(data);
      HermesReplyErr(id,"pull_size");
      return;
    }
    HermesReplyLen(id,data,size);
    Free(data);
  }
  else if (!StrICmp(op,"push"))
  {
    i=0;
    while (i<len && payload[i]) i++;
    if (i>=len)
    {
      HermesReplyErr(id,"push_path");
      return;
    }
    path=payload;
    data=payload+i+1;
    wrote=FileWrite(path,data,len-i-1);
    if (wrote<0)
    {
      HermesReplyErr(id,"push_write");
      return;
    }
    res=MStrPrint("{\"wrote\":%d}",wrote);
    HermesReply(id,res);
    Free(res);
  }
  else if (!StrICmp(op,"events"))
  {
    res=HermesEventsDrainJSON;
    HermesReply(id,res);
    Free(res);
  }
  else if (!StrICmp(op,"idle"))
  {
    res=HermesIdleJSON;
    HermesReply(id,res);
    Free(res);
  }
  else
    HermesReplyErr(id,"unknown_op");
}

U0 HermesHandleLine(U8 *line)
{
  U8 *p,op[32];
  I64 id,len,i,n;
  U8 *payload,ch;
  p=line;
  if (StrNCmp(p,"HREQ ",5))
    return;
  p+=5;
  id=Str2I64(p);
  while (*p && *p!=' ') p++;
  while (*p==' ') p++;
  i=0;
  while (*p && *p!=' ' && i<31)
    op[i++]=*p++;
  op[i]=0;
  while (*p==' ') p++;
  len=Str2I64(p);
  if (len<0 || len>HERMES_MAX_PAYLOAD)
  {
    HermesReplyErr(id,"len");
    return;
  }
  payload=MAlloc(len+1);
  for (n=0; n<len; n++)
  {
    ch=HermesGetChar;
    payload[n]=ch;
  }
  payload[len]=0;
  HermesHandle(id,op,payload,len);
  Free(payload);
}

U0 HermesDaemonTask()
{
  U8 ch;
  hermes_task=Fs;
  Fs->task_name[0]=0;
  StrCpy(Fs->task_title,"HermesDaemon");
  LBtr(&Fs->display_flags,DISPLAYf_SHOW);
  hermes_ready=TRUE;
  HermesBeacon;
  HermesEventPush("ready",HERMES_VERSION);
  HermesEventsFlush;
  while (TRUE)
  {
    HermesPollEvents;
    if (HermesGetCharNoWait(&ch))
    {
      if (ch=='\n')
      {
        hermes_line[hermes_line_n]=0;
        if (hermes_line_n>0)
          HermesHandleLine(hermes_line);
        hermes_line_n=0;
      }
      else if (ch!='\r')
      {
        if (hermes_line_n<HERMES_LINE_MAX-1)
          hermes_line[hermes_line_n++]=ch;
        else
          hermes_line_n=0;
      }
    }
    else
      Yield;
  }
}

U0 HermesInit()
{
  if (hermes_started)
    return;
  hermes_started=TRUE;
  hermes_mode=HERMES_MODE_USER;
  hermes_last_prompt[0]=0;
  try
  {
    CommInit;
    CommInit8n1(HERMES_COM,HERMES_BAUD);
  }
  catch
    Fs->catch_except=TRUE;
  HermesPresenceInstall;
  HermesGuardsInstall;
  Spawn(&HermesDaemonTask,NULL,"HermesDaemon");
}
