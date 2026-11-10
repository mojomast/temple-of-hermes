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
  SpMkdir("C:/Tmp");
  return "C:/Tmp/";
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
  U8 *path=MStrPrint("%sSpoonScore.TXT",SpHome());
  I64 n=0,v=0;
  U8 *b=FileRead(path,&n);
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
  U8 *path=MStrPrint("%sSpoonScore.TXT",SpHome());
  StrPrint(buf,"%d\n",high);
  FileWrite(path,buf,StrLen(buf));
  Free(path);
}

#endif
