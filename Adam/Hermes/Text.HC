// Exact DolDoc text export for the focused window or every visible window.

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


U8 *HermesDocPlain(CDoc *doc)
{
  U8 *st,*out_prev,*out=NULL;
  CDocEntry *doc_e,*doc_e2;
  Bool unlock;
  if (!doc || doc->doc_signature!=DOC_SIGNATURE_VAL)
    return StrNew("");
  unlock=DocLock(doc);
  doc_e=doc->head.next;
  out_prev=StrNew("");
  while (doc_e!=doc)
  {
    st=DocScanLine(doc,doc_e,NULL,&doc_e2);
    out=MStrPrint("%s%s",out_prev,st);
    Free(out_prev);
    Free(st);
    out_prev=out;
    doc_e=doc_e2;
    if (doc_e->type_u8==DOCT_NEW_LINE)
    {
      out=MStrPrint("%s\n",out_prev);
      Free(out_prev);
      out_prev=out;
      doc_e=doc_e->next;
    }
  }
  if (unlock)
    DocUnlock(doc);
  return out_prev;
}

U8 *HermesDocJSON(CTask *task)
{
  CDoc *doc;
  U8 *text,*esc,*title,*name,*out;
  I64 cx=0,cy=0,line=0,col=0;
  if (!TaskValidate(task))
    return StrNew("{}");
  title=HermesEsc(task->task_title);
  name=HermesEsc(task->task_name);
  doc=DocPut(task);
  if (doc && doc->doc_signature==DOC_SIGNATURE_VAL)
  {
    text=HermesDocPlain(doc);
    if (!text) text=StrNew("");
    esc=HermesEsc(text);
    Free(text);
    cx=doc->x;
    cy=doc->y;
    line=doc->line;
    col=doc->cur_col;
    out=MStrPrint(
      "{\"addr\":\"0x%X\",\"name\":\"%s\",\"title\":\"%s\","
      "\"win\":[%d,%d,%d,%d],\"focus\":%d,"
      "\"cursor\":{\"x\":%d,\"y\":%d,\"line\":%d,\"col\":%d},"
      "\"text\":\"%s\"}",
      task,name,title,
      task->win_left,task->win_top,task->win_right,task->win_bottom,
      task==sys_focus_task,
      cx,cy,line,col,esc);
    Free(esc);
  }
  else
  {
    out=MStrPrint(
      "{\"addr\":\"0x%X\",\"name\":\"%s\",\"title\":\"%s\","
      "\"win\":[%d,%d,%d,%d],\"focus\":%d,\"text\":\"\"}",
      task,name,title,
      task->win_left,task->win_top,task->win_right,task->win_bottom,
      task==sys_focus_task);
  }
  Free(title);
  Free(name);
  return out;
}

U8 *HermesTextFocus()
{
  if (TaskValidate(sys_focus_task))
    return HermesDocJSON(sys_focus_task);
  return StrNew("{\"error\":\"no_focus\"}");
}

U8 *HermesTextAll()
{
  CTask *task;
  U8 *out,*one,*tmp;
  I64 first=TRUE;
  out=StrNew("{\"windows\":[");
  if (adam_task)
  {
    task=adam_task;
    do
    {
      if (HermesTaskIsWindow(task))
      {
        one=HermesDocJSON(task);
        if (first)
          tmp=MStrPrint("%s%s",out,one);
        else
          tmp=MStrPrint("%s,%s",out,one);
        first=FALSE;
        Free(out);
        Free(one);
        out=tmp;
      }
      task=task->next_task;
    }
    while (task!=adam_task && TaskValidate(task));
  }
  tmp=MStrPrint("%s]}",out);
  Free(out);
  return tmp;
}

I64 HermesCountTasks()
{
  CTask *task;
  I64 n=0;
  if (adam_task)
  {
    task=adam_task;
    do
    {
      if (TaskValidate(task))
        n++;
      task=task->next_task;
    }
    while (task!=adam_task && TaskValidate(task));
  }
  return n;
}

I64 HermesCountWindows()
{
  CTask *task;
  I64 n=0;
  if (adam_task)
  {
    task=adam_task;
    do
    {
      if (HermesTaskIsWindow(task))
        n++;
      task=task->next_task;
    }
    while (task!=adam_task && TaskValidate(task));
  }
  return n;
}

U8 *HermesWindowJSON(CTask *task)
{
  U8 *title,*name,*out;
  CDoc *doc;
  I64 cx=0,cy=0,line=0,col=0;
  if (!TaskValidate(task))
    return StrNew("{}");
  title=HermesEsc(task->task_title);
  name=HermesEsc(task->task_name);
  doc=DocPut(task);
  if (doc && doc->doc_signature==DOC_SIGNATURE_VAL)
  {
    cx=doc->x;
    cy=doc->y;
    line=doc->line;
    col=doc->cur_col;
  }
  out=MStrPrint(
    "{\"addr\":\"0x%X\",\"name\":\"%s\",\"title\":\"%s\","
    "\"win\":[%d,%d,%d,%d],\"show\":%d,\"focus\":%d,\"z\":%d,"
    "\"cursor\":{\"x\":%d,\"y\":%d,\"line\":%d,\"col\":%d}}",
    task,name,title,
    task->win_left,task->win_top,task->win_right,task->win_bottom,
    Bt(&task->display_flags,DISPLAYf_SHOW),
    task==sys_focus_task,task->win_z_num,
    cx,cy,line,col);
  Free(title);
  Free(name);
  return out;
}

U8 *HermesWindowsJSON()
{
  CTask *task;
  U8 *out,*one,*tmp;
  I64 first=TRUE;
  out=StrNew("{\"focus\":\"0x%X\",\"windows\":[");
  tmp=MStrPrint(out,sys_focus_task);
  Free(out);
  out=tmp;
  if (adam_task)
  {
    task=adam_task;
    do
    {
      if (HermesTaskIsWindow(task))
      {
        one=HermesWindowJSON(task);
        if (first)
          tmp=MStrPrint("%s%s",out,one);
        else
          tmp=MStrPrint("%s,%s",out,one);
        first=FALSE;
        Free(out);
        Free(one);
        out=tmp;
      }
      task=task->next_task;
    }
    while (task!=adam_task && TaskValidate(task));
  }
  tmp=MStrPrint("%s]}",out);
  Free(out);
  return tmp;
}

U8 *HermesTasksJSON()
{
  CTask *task;
  U8 *out,*tmp,*title,*name;
  I64 first=TRUE;
  out=StrNew("{\"focus\":\"0x%X\",\"tasks\":[");
  tmp=MStrPrint(out,sys_focus_task);
  Free(out);
  out=tmp;
  if (adam_task)
  {
    task=adam_task;
    do
    {
      if (TaskValidate(task))
      {
        title=HermesEsc(task->task_title);
        name=HermesEsc(task->task_name);
        if (first)
          tmp=MStrPrint(
            "%s{\"addr\":\"0x%X\",\"name\":\"%s\",\"title\":\"%s\","
            "\"win\":[%d,%d,%d,%d],\"show\":%d,\"focus\":%d}",
            out,task,name,title,
            task->win_left,task->win_top,task->win_right,task->win_bottom,
            Bt(&task->display_flags,DISPLAYf_SHOW),
            task==sys_focus_task);
        else
          tmp=MStrPrint(
            "%s,{\"addr\":\"0x%X\",\"name\":\"%s\",\"title\":\"%s\","
            "\"win\":[%d,%d,%d,%d],\"show\":%d,\"focus\":%d}",
            out,task,name,title,
            task->win_left,task->win_top,task->win_right,task->win_bottom,
            Bt(&task->display_flags,DISPLAYf_SHOW),
            task==sys_focus_task);
        first=FALSE;
        Free(out);
        Free(title);
        Free(name);
        out=tmp;
      }
      task=task->next_task;
    }
    while (task!=adam_task && TaskValidate(task));
  }
  tmp=MStrPrint("%s]}",out);
  Free(out);
  return tmp;
}
