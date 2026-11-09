// Event ring and poller: task spawn, window open, prompt waiting.

U0 HermesEventPush(U8 *kind,U8 *data)
{
  CHermesEvt *e;
  I64 next;
  if (!kind) kind="unknown";
  if (!data) data="";
  next=(hermes_evt_head+1)%HERMES_MAX_EVT;
  if (next==hermes_evt_tail)
    hermes_evt_tail=(hermes_evt_tail+1)%HERMES_MAX_EVT;
  e=&hermes_evts[hermes_evt_head];
  hermes_evt_seq++;
  e->seq=hermes_evt_seq;
  e->t=tS;
  StrPrint(e->kind,"%s",kind);
  e->kind[31]=0;
  StrPrint(e->data,"%s",data);
  e->data[191]=0;
  hermes_evt_head=next;
}

U0 HermesEventEmit(CHermesEvt *e)
{
  U8 json[320], *ks, *ds;
  I64 len;
  ks=HermesEsc(e->kind);
  ds=HermesEsc(e->data);
  StrPrint(json,"{\"seq\":%d,\"t\":%7.3f,\"kind\":\"%s\",\"data\":\"%s\"}",
           e->seq,e->t,ks,ds);
  Free(ks);
  Free(ds);
  len=StrLen(json);
  HermesSendRaw("HEVT",e->seq,e->kind,json,len);
}

U0 HermesEventsFlush()
{
  CHermesEvt *e;
  while (hermes_evt_tail!=hermes_evt_head)
  {
    e=&hermes_evts[hermes_evt_tail];
    HermesEventEmit(e);
    hermes_evt_tail=(hermes_evt_tail+1)%HERMES_MAX_EVT;
  }
}

U8 *HermesEventsDrainJSON()
{
  U8 *out,*tmp,*ks,*ds;
  CHermesEvt *e;
  I64 first=TRUE;
  out=StrNew("[");
  while (hermes_evt_tail!=hermes_evt_head)
  {
    e=&hermes_evts[hermes_evt_tail];
    ks=HermesEsc(e->kind);
    ds=HermesEsc(e->data);
    if (first)
      tmp=MStrPrint("%s{\"seq\":%d,\"t\":%7.3f,\"kind\":\"%s\",\"data\":\"%s\"}",
                    out,e->seq,e->t,ks,ds);
    else
      tmp=MStrPrint("%s,{\"seq\":%d,\"t\":%7.3f,\"kind\":\"%s\",\"data\":\"%s\"}",
                    out,e->seq,e->t,ks,ds);
    first=FALSE;
    Free(out);
    Free(ks);
    Free(ds);
    out=tmp;
    hermes_evt_tail=(hermes_evt_tail+1)%HERMES_MAX_EVT;
  }
  tmp=MStrPrint("%s]",out);
  Free(out);
  return tmp;
}

Bool HermesTaskIsWindow(CTask *task)
{
  if (!task || !TaskValidate(task))
    return FALSE;
  if (task==hermes_task)
    return FALSE;
  if (!Bt(&task->display_flags,DISPLAYf_SHOW))
    return FALSE;
  if (task==sys_winmgr_task)
    return FALSE;
  return TRUE;
}

U0 HermesPollTasks()
{
  CTask *task;
  I64 now[HERMES_MAX_TASKS],n=0,i,j,found;
  U8 buf[192];
  if (!adam_task) return;
  task=adam_task;
  do
  {
    if (TaskValidate(task) && n<HERMES_MAX_TASKS)
    {
      now[n++]=task;
    }
    task=task->next_task;
  }
  while (task!=adam_task && TaskValidate(task));

  if (!hermes_seen_cnt)
  {
    for (i=0; i<n; i++)
      hermes_seen_tasks[i]=now[i];
    hermes_seen_cnt=n;
    return;
  }

  for (i=0; i<n; i++)
  {
    found=FALSE;
    for (j=0; j<hermes_seen_cnt; j++)
      if (hermes_seen_tasks[j]==now[i])
        found=TRUE;
    if (!found && TaskValidate(now[i](CTask *)))
    {
      task=now[i](CTask *);
      StrPrint(buf,"0x%X %s",task,task->task_title);
      HermesEventPush("task_spawned",buf);
      if (HermesTaskIsWindow(task))
        HermesEventPush("window_opened",buf);
    }
  }
  for (i=0; i<n; i++)
    hermes_seen_tasks[i]=now[i];
  hermes_seen_cnt=n;
}

U0 HermesPollPrompt()
{
  CDoc *doc;
  U8 *st,snip[256];
  I64 len,off;
  if (!TaskValidate(sys_focus_task))
    return;
  doc=DocPut(sys_focus_task);
  if (!doc)
    return;
  st=HermesDocPlain(doc);
  if (!st) return;
  len=StrLen(st);
  off=len-200;
  if (off<0) off=0;
  StrPrint(snip,"%s",st+off);
  if (StrIMatch("(y or n)",st) ||
      StrIMatch("ARE YOU SURE",st) ||
      StrIMatch("Install onto hard drive",st) ||
      StrIMatch("Press a key",st))
  {
    if (!hermes_prompt_armed || StrCmp(hermes_last_prompt,snip))
    {
      StrPrint(hermes_last_prompt,"%s",snip);
      hermes_last_prompt[255]=0;
      hermes_prompt_armed=TRUE;
      HermesEventPush("prompt_waiting",snip);
    }
  }
  else
    hermes_prompt_armed=FALSE;
  Free(st);
}

U0 HermesPollEvents()
{
  HermesPollTasks;
  HermesPollPrompt;
  HermesEventsFlush;
}
