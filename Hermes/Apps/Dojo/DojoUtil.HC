#ifndef DOJO_UTIL_HC
#define DOJO_UTIL_HC
#include "Dojo.HC"
#include "DojoSmall.HC"
U8 *DojoPath(U8 *rel)
{//Look for the official art-nous asset first, then the app directory.
  I64 i;
  U8 *st,*roots[4]={"::/Hermes/Art/","T:/Hermes/Art/","C:/Hermes/Art/","~/Hermes/Art/"};
  for (i=0;i<4;i++)
  {
    st=MStrPrint("%s%s",roots[i],rel);
    if (IsFile(st))
      return st;
    Free(st);
  }
  return MStrPrint("%s/%s",__DIR__,rel);
}
U8 *DojoAgent(U8 *rel)
{
  if (*rel)
    return MStrPrint("%s/Agent/%s",__DIR__,rel);
  return MStrPrint("%s/Agent",__DIR__);
}
U0 DojoWriteResult(I64 n,U8 *title,I64 score,Bool pass,U8 *detail)
{
  U8 *dir=DojoAgent("");
  U8 *path=MStrPrint("%s/result%d.txt",dir,n);
  U8 *buf=MStrPrint("CHALLENGE: %s\nSTATUS: %s\nSCORE: %d\nDETAIL: %s\n",
        title,DojoYN(pass),score,detail);
  if (!FileFind(dir)) DirMk(dir);
  FileWrite(path,buf,StrLen(buf));
  Free(buf); Free(path); Free(dir);
}
U8 *DojoResultText(I64 n)
{
  U8 *dir=DojoAgent(""),*p=MStrPrint("%s/result%d.txt",dir,n);
  U8 *b=NULL;
  if (FileFind(p)) b=FileRead(p);
  Free(p); Free(dir);
  return b;
}
I64 DojoStatus(I64 n)
{
  U8 *b=DojoResultText(n);
  if (!b) return -1;
  I64 r=0;
  if (StrFind("STATUS: PASS",b)) r=1;
  Free(b);
  return r;
}
I64 DojoScoreOf(I64 n)
{
  U8 *b=DojoResultText(n);
  if (!b) return -1;
  I64 s=-1; U8 *q=StrFind("SCORE: ",b);
  if (q) s=Str2I64(q+7);
  Free(b);
  return s;
}
#endif
