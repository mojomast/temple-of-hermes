#ifndef HERMES_APPS_PATHS_HC
#define HERMES_APPS_PATHS_HC

U8 *hermes_apps_roots[4]={"::/Hermes/","T:/Hermes/","C:/Hermes/","~/Hermes/"};

public U8 *HermesAppsFind(U8 *rel)
{//Find rel under the Hermes tree.  Returns an allocated full path or NULL.
  I64 i;
  U8 *st;
  for (i=0;i<4;i++)
  {
    st=MStrPrint("%s%s",hermes_apps_roots[i],rel);
    if (IsFile(st))
      return st;
    Free(st);
  }
  return NULL;
}

#endif
