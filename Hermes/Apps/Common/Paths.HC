#ifndef HERMES_APPS_PATHS_HC
#define HERMES_APPS_PATHS_HC

U8 *hermes_apps_roots[4]={"::/Hermes/","T:/Hermes/","C:/Hermes/","~/Hermes/"};


public U8 *HermesAppsAbsPath(U8 *rel)
{//Turn ::/ and ~/ into an explicit drive letter.  ExeFile() from a spawned
//task is reliable with C:/... on disk and T:/... on the live CD, while a
//::/ path can leave the task spinning before the app draws.
  U8 let;
  if (!rel || !*rel)
    return StrNew("");
  if (rel[0]==':' && rel[1]==':')
  {
    let=Drv2Let(Let2Drv(':',FALSE));
    if (let)
      return MStrPrint("%c:/%s",let,rel+3);
  }
  else if (rel[0]=='~' && rel[1]=='/')
  {
    let=Drv2Let(Let2Drv('~',FALSE));
    if (let)
      return MStrPrint("%c:/%s",let,rel+2);
  }
  return StrNew(rel);
}

public U8 *HermesAppsFind(U8 *rel)
{//Find rel under the Hermes tree.  Returns an allocated full path or NULL.
//Exact absolute paths win; otherwise search the legacy roots and every
//mounted FAT/ISO drive so a live CD and an installed disk use one code path.
  I64 i;
  U8 *st,*dletters;
  U8 dletter;
  if (!rel || !*rel)
    return NULL;
  dletters="ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  if ((rel[0]=='~' && rel[1]=='/') || rel[1]==':')
  {
    if (IsFile(rel))
      return HermesAppsAbsPath(rel);
    if (rel[1]==':' && rel[2]=='/')
      rel+=3;
    else if (rel[0]=='~' && rel[1]=='/')
      rel+=2;
  }
  for (i=0;i<4;i++)
  {
    st=MStrPrint("%s%s",hermes_apps_roots[i],rel);
    if (IsFile(st))
    {
      if (st[0]==':' && st[1]==':')
      {
        U8 *abs=HermesAppsAbsPath(st);
        Free(st);
        return abs;
      }
      return st;
    }
    Free(st);
  }
  for (i=0;i<26;i++)
  {
    if (Let2Drv(dletters[i],FALSE))
    {
      dletter=dletters[i];
      st=MStrPrint("%c:/Hermes/%s",dletter,rel);
      if (IsFile(st))
        return st;
      Free(st);
    }
  }
  return NULL;
}

#endif
