#ifndef HERMES_OFFERINGS_ART_HC
#define HERMES_OFFERINGS_ART_HC

U8 *offer_roots[5]={"::/Hermes/","T:/Hermes/","C:/Hermes/","~/Hermes/","B:/Hermes/"};

U8 *OfferOrEmpty(U8 *s)
{//Never return NULL to a %s formatter.
  if (s)
    return s;
  return "";
}

U8 *OfferUpper(U8 *st)
{//Uppercase the file name part for FAT 8.3 names without an LFN.
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

U8 *OfferFind(U8 *rel)
{//Find rel under the Hermes tree.  Returns an allocated path or NULL.
  I64 i;
  U8 *st,*up;
  if (!rel)
    return NULL;
  for (i=0;i<5;i++)
  {
    st=MStrPrint("%s%s",offer_roots[i],rel);
    if (IsFile(st))
      return st;
    Free(st);
  }
  up=OfferUpper(rel);
  for (i=0;i<5;i++)
  {
    st=MStrPrint("%s%s",offer_roots[i],up);
    if (IsFile(st))
    {
      Free(up);
      return st;
    }
    Free(st);
  }
  Free(up);
  return NULL;
}

U0 OfferMkDir(U8 *path)
{//DirMk throws on a read-only drive; a missing profile is not fatal.
  try
  {
    DirMk(path);
  }
  catch
  {
  }
}

U8 *OfferHome()
{//Writable shop profile.  Never touches Adam or Hermes/Art.
  OfferMkDir("C:/Tmp");
  OfferMkDir("C:/Tmp/Offerings");
  OfferMkDir("C:/Tmp/Offerings/Wallpapers");
  OfferMkDir("C:/Tmp/Offerings/Palettes");
  OfferMkDir("C:/Tmp/Offerings/Snippets");
  OfferMkDir("C:/Tmp/Offerings/Results");
  return StrNew("C:/Tmp/Offerings/");
}

U8 *OfferSourcePath(COfferItem *it)
{
  if (!it)
    return NULL;
  return OfferFind(it->src);
}

CDC *OfferLoadPlate()
{
  U8 *st;
  CDC *dc=NULL;
  st=OfferFind("Art/UI/header-offerings-plate.GR");
  if (st)
  {
    dc=GRRead(st);
    Free(st);
  }
  return dc;
}

CDC *OfferLoadPiedro(I64 size=32)
{
  U8 *rel,*st;
  CDC *dc=NULL;
  rel=MStrPrint("Art/Icons/%d/don-piedro.GR",size);
  st=OfferFind(rel);
  Free(rel);
  if (st)
  {
    dc=GRRead(st);
    Free(st);
  }
  return dc;
}

CDC *OfferLoadWall(U8 *rel)
{
  U8 *st;
  CDC *dc=NULL;
  st=OfferFind(rel);
  if (st)
  {
    dc=GRRead(st);
    Free(st);
  }
  return dc;
}

U8 *offer_pal_name[16]={
  "BLACK","BLUE","GREEN","CYAN","RED","PURPLE","BROWN","LTGRAY",
  "DKGRAY","LTBLUE","LTGREEN","LTCYAN","LTRED","LTPURPLE","YELLOW","WHITE"
};


#endif
