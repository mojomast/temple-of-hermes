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
        tmp=MStrPrint("%s{\"name\":\"%s\",\"is_dir\":%d}",
                      buf,esc,!!(de->attr & RS_ATTR_DIR));
      else
        tmp=MStrPrint("%s,{\"name\":\"%s\",\"is_dir\":%d}",
                      buf,esc,!!(de->attr & RS_ATTR_DIR));
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
