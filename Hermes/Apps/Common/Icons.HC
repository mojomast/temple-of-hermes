#ifndef HERMES_APPS_ICONS_HC
#define HERMES_APPS_ICONS_HC

U8 *HermesAppsUpper(U8 *st)
{//Uppercase the file name part only, for FAT 8.3 names without an LFN.
  U8 *res,*p,*base;
  res=StrNew(st);
  p=res;
  base=res;
  while (*p)
  {
    if (*p=='/')
      base=p+1;
    p++;
  }
  while (*base)
  {
    *base=ToUpper(*base);
    base++;
  }
  return res;
}

public CDC *HermesAppsIcon(U8 *name,I64 size=32)
{//Load Hermes/Art/Icons/<size>/<name>.GR.  Returns NULL if missing.
  U8 *rel,*st,*up;
  CDC *dc=NULL;
  rel=MStrPrint("Art/Icons/%d/%s.GR",size,name);
  st=HermesAppsFind(rel);
  if (!st)
  {
    up=HermesAppsUpper(rel);
    st=HermesAppsFind(up);
    Free(up);
  }
  Free(rel);
  if (st)
  {
    dc=GRRead(st);
    Free(st);
  }
  return dc;
}

#endif
