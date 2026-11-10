// Serial file list / pull / push, used by the daemon and the plugin.

U8 *HermesListDir(U8 *path)
{
  U8 *buf,*tmp,*esc;
  I64 first=TRUE;
  CDirEntry *tree=NULL,*de;
  if (!path || !*path) path="/";
  buf=StrNew("[");
  try
  {
    tree=FilesFind(path);
    de=tree;
    while (de)
    {
      esc=HermesEsc(de->name);
      if (first)
        tmp=MStrPrint("%s{\"name\":\"%s\",\"is_dir\":%d,\"size\":%d,\"attr\":%d,\"datetime\":%d}",
                      buf,esc,!!(de->attr & RS_ATTR_DIR),de->size,de->attr,de->datetime);
      else
        tmp=MStrPrint("%s,{\"name\":\"%s\",\"is_dir\":%d,\"size\":%d,\"attr\":%d,\"datetime\":%d}",
                      buf,esc,!!(de->attr & RS_ATTR_DIR),de->size,de->attr,de->datetime);
      first=FALSE;
      Free(buf);
      Free(esc);
      buf=tmp;
      de=de->next;
    }
  }
  catch
    Fs->catch_except=TRUE;
  if (tree) DirTreeDel(tree);
  tmp=MStrPrint("%s]",buf);
  Free(buf);
  return tmp;
}

U8 *HermesClipGet()
{
  U8 *st,*esc,*out;
  st=HermesDocPlain(sys_clip_doc);
  if (!st) st=StrNew("");
  esc=HermesEsc(st);
  out=MStrPrint("{\"text\":\"%s\"}",esc);
  Free(st);
  Free(esc);
  return out;
}

U0 HermesClipSet(U8 *s)
{
  Bool unlock;
  if (!s) s="";
  ClipDel;
  unlock=DocLock(sys_clip_doc);
  sys_clip_doc->flags|=DOCF_PLAIN_TEXT;
  DocPrint(sys_clip_doc,"%s",s);
  if (unlock)
    DocUnlock(sys_clip_doc);
}

U8 *HermesStatJSON(U8 *path)
{
  CDirEntry de;
  U8 *pe,*ne,*out;
  if (!path || !*path) path="/";
  MemSet(&de,0,sizeof(de));
  pe=HermesEsc(path);
  if (!FileFind(path,&de))
  {
    out=MStrPrint("{\"path\":\"%s\",\"exists\":0}",pe);
    Free(pe);
    return out;
  }
  ne=HermesEsc(de.name);
  out=MStrPrint(
    "{\"path\":\"%s\",\"exists\":1,\"name\":\"%s\",\"size\":%d,"
    "\"attr\":%d,\"is_dir\":%d,\"datetime\":%d}",
    pe,ne,de.size,de.attr,!!(de.attr & RS_ATTR_DIR),de.datetime);
  Free(pe);
  Free(ne);
  return out;
}

U8 *HermesDocReadJSON(U8 *path)
{
  CDoc *doc;
  Bool del=FALSE;
  U8 *dol,*text,*edol,*etext,*epath,*out,*pname;
  I64 size=0;
  if (!path || !*path)
    doc=DocPut(sys_focus_task);
  else
  {
    doc=DocRead(path);
    del=TRUE;
  }
  if (!doc || doc->doc_signature!=DOC_SIGNATURE_VAL)
    return StrNew("{\"ok\":0,\"error\":\"doc_read\"}");
  dol=DocSave(doc,&size);
  if (!dol) dol=StrNew("");
  text=HermesDocPlain(doc);
  if (!text) text=StrNew("");
  edol=HermesEsc(dol);
  etext=HermesEsc(text);
  if (path && *path)
    pname=path;
  else
    pname="focus";
  epath=HermesEsc(pname);
  out=MStrPrint(
    "{\"ok\":1,\"path\":\"%s\",\"size\":%d,\"dol\":\"%s\",\"text\":\"%s\"}",
    epath,size,edol,etext);
  Free(dol);
  Free(text);
  Free(edol);
  Free(etext);
  Free(epath);
  if (del && !doc->win_task)
    DocDel(doc);
  return out;
}

U8 *HermesSysInfoJSON()
{
  CDateStruct ds;
  U8 *out;
  Date2Struct(&ds,Now+local_time_offset);
  out=MStrPrint(
    "{\"name\":\"" HERMES_NAME "\",\"version\":\"" HERMES_VERSION "\","
    "\"os_version\":%0.3f,\"t\":%7.3f,"
    "\"time\":\"%04d-%02d-%02dT%02d:%02d:%02d\","
    "\"mode\":\"%s\",\"ready\":%d,"
    "\"tasks\":%d,\"windows\":%d,\"tasks_spawned\":%d,"
    "\"mem_phys\":%d,\"heap_base\":\"0x%X\",\"heap_limit\":\"0x%X\","
    "\"screen\":{\"w\":%d,\"h\":%d,\"cols\":%d,\"rows\":%d},"
    "\"com\":{\"port\":%d,\"baud\":%d},"
    "\"build\":{\"compiler\":\"HolyC\"}}",
    sys_os_version,tS,
    ds.year,ds.mon,ds.day_of_mon,ds.hour,ds.min,ds.sec,
    HermesModeName,hermes_ready,
    HermesCountTasks(),HermesCountWindows(),sys_num_spawned_tasks,
    mem_physical_space(I64),mem_heap_base(I64),mem_heap_limit(I64),
    GR_WIDTH,GR_HEIGHT,GR_WIDTH/FONT_WIDTH,GR_HEIGHT/FONT_HEIGHT,
    HERMES_COM,HERMES_BAUD);
  return out;
}
