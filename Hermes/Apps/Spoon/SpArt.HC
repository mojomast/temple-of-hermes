#ifndef SP_ART_HC
#define SP_ART_HC

U8 *sp_roots[4]={"C:/Hermes/","T:/Hermes/","::/Hermes/","~/Hermes/"};

U0 SpMkdir(U8 *path)
{
  try
  {
    DirMk(path);
  }
  catch
  {
  }
}

U8 *SpHome()
{
  U8 *dir=HermesStateDir("Spoon"),*st;
  if (!dir || !*dir)
  {
    if (dir)
      Free(dir);
    return StrNew("");
  }
  st=MStrPrint("%s/",dir);
  Free(dir);
  return st;
}

U8 *SpFind(U8 *rel)
{
  I64 i;
  U8 *st;
  if (!rel)
    return NULL;
  for (i=0;i<4;i++)
  {
    st=MStrPrint("%s%s",sp_roots[i],rel);
    if (IsFile(st))
      return st;
    Free(st);
  }
  return NULL;
}

CDC *SpLoadPlate()
{
  U8 *st=SpFind("Art/UI/header-offerings-plate.GR");
  CDC *dc=NULL;
  if (st)
  {
    dc=GRRead(st);
    Free(st);
  }
  return dc;
}

CDC *SpLoadPiedro(I64 size=64)
{
  U8 *rel=MStrPrint("Art/Icons/%d/don-piedro.GR",size);
  U8 *st=SpFind(rel);
  CDC *dc=NULL;
  Free(rel);
  if (st)
  {
    dc=GRRead(st);
    Free(st);
  }
  return dc;
}

I64 SpReadHigh()
{
  U8 *home=SpHome(),*path;
  I64 n=0,v=0;
  U8 *b;
  if (!home || !*home)
  {
    if (home)
      Free(home);
    return 0;
  }
  path=MStrPrint("%sSpoonScore.TXT",home);
  Free(home);
  b=NULL;
  if (FileFind(path))
    b=FileRead(path,&n);
  if (b)
  {
    v=Str2I64(b);
    Free(b);
  }
  Free(path);
  return v;
}

U0 SpWriteHigh(I64 high)
{
  U8 buf[64];
  U8 *home=SpHome(),*path;
  if (!home || !*home)
  {
    if (home)
      Free(home);
    return;
  }
  path=MStrPrint("%sSpoonScore.TXT",home);
  Free(home);
  StrPrint(buf,"%d\n",high);
  try
  {
    FileWrite(path,buf,StrLen(buf));
  }
  catch
    Fs->catch_except=TRUE;
  Free(path);
}

#endif
