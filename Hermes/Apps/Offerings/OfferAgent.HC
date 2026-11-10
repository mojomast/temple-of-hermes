#ifndef HERMES_OFFERINGS_AGENT_HC
#define HERMES_OFFERINGS_AGENT_HC

U8 *OfferingsResultDir()
{
  U8 *home=OfferHome();
  U8 *dir=MStrPrint("%sResults/",home);
  Free(home);
  return dir;
}

U0 OfferingsNoteInstalled(COfferItem *it)
{
  U8 *home,*path,*line,*old,*buf;
  I64 old_n=0,line_n;
  if (!it)
    return;
  home=OfferHome();
  path=MStrPrint("%sinstalled.txt",home);
  line=MStrPrint("%s|%s|%s\n",it->id,it->title,it->dest);
  line_n=StrLen(line);
  old=NULL;
  old_n=0;
  if (IsFile(path))
    old=FileRead(path,&old_n);
  buf=MAlloc(old_n+line_n+1);
  if (old)
  {
    MemCpy(buf,old,old_n);
    Free(old);
  }
  MemCpy(buf+old_n,line,line_n);
  buf[old_n+line_n]=0;
  FileWrite(path,buf,old_n+line_n);
  Free(buf);
  Free(line);
  Free(path);
  Free(home);
}

Bool OfferInstall(COfferItem *it)
{
  U8 *src,*home,*dest,*data;
  I64 size=0;
  if (!it)
    return FALSE;
  src=OfferSourcePath(it);
  if (!src)
    return FALSE;
  home=OfferHome();
  dest=MStrPrint("%s%s",home,it->dest);
  data=FileRead(src,&size);
  if (!data)
  {
    Free(src);
    Free(home);
    Free(dest);
    return FALSE;
  }
  FileWrite(dest,data,size);
  Free(data);
  it->installed=IsFile(dest);
  if (it->installed)
    OfferingsNoteInstalled(it);
  Free(src);
  Free(home);
  Free(dest);
  return it->installed;
}

U8 *OfferingsCatalogJson()
{
  U8 *buf,*src,*home,*dest;
  I64 i;
  COfferItem *it;
  OfferingsInit;
  buf=MAlloc(24576);
  buf[0]=0;
  StrPrint(buf,
    "{\"v\":1,\"app\":\"offerings\",\"ok\":1,\"currency\":\"spoons\","
    "\"real_money\":false,\"count\":%d,\"items\":[",offer_count);
  for (i=0;i<offer_count;i++)
  {
    it=&offer_items[i];
    if (i)
      CatPrint(buf,",");
    src=OfferSourcePath(it);
    home=OfferHome();
    dest=MStrPrint("%s%s",home,it->dest);
    CatPrint(buf,
      "{\"id\":\"%s\",\"kind\":\"%s\",\"cat\":\"%s\",\"title\":\"%s\","
      "\"price_spoons\":%d,\"new\":%d,\"installed\":%d,"
      "\"src\":\"%s\",\"src_path\":\"%s\",\"dest\":\"%s\",\"dest_path\":\"%s\"}",
      it->id,it->kind,OfferCatName(it->cat),it->title,it->price,
      it->is_new,it->installed,it->src,OfferOrEmpty(src),it->dest,dest);
    Free(src);
    Free(dest);
    Free(home);
  }
  CatPrint(buf,"]}\n");
  return buf;
}

U0 OfferingsWriteJson(U8 *name,U8 *json)
{
  U8 *dir,*path,*last;
  dir=OfferingsResultDir();
  path=MStrPrint("%s%s",dir,name);
  last=MStrPrint("%slast.json",dir);
  FileWrite(path,json,StrLen(json));
  FileWrite(last,json,StrLen(json));
  "Offerings result: %s\n",path;
  Free(last);
  Free(path);
  Free(dir);
}

U0 OfferingsList()
{//Agent hook: write the whole catalog and every file path.
  U8 *json;
  OfferingsInit;
  json=OfferingsCatalogJson();
  OfferingsWriteJson("list.json",json);
  Free(json);
}

U0 OfferingsGet(U8 *id)
{//Agent hook: write one item, including its source and install paths.
  COfferItem *it;
  U8 *json,*src,*home,*dest,*name;
  it=OfferFindItem(id);
  json=MAlloc(4096);
  if (!it)
  {
    StrPrint(json,
      "{\"v\":1,\"app\":\"offerings\",\"op\":\"get\",\"ok\":0,"
      "\"error\":\"not_found\",\"id\":\"%s\"}\n",OfferOrEmpty(id));
    OfferingsWriteJson("get.json",json);
    Free(json);
    return;
  }
  src=OfferSourcePath(it);
  home=OfferHome();
  dest=MStrPrint("%s%s",home,it->dest);
  StrPrint(json,
    "{\"v\":1,\"app\":\"offerings\",\"op\":\"get\",\"ok\":1,"
    "\"currency\":\"spoons\",\"real_money\":false,"
    "\"item\":{\"id\":\"%s\",\"kind\":\"%s\",\"cat\":\"%s\","
    "\"title\":\"%s\",\"blurb\":\"%s\",\"price_spoons\":%d,"
    "\"new\":%d,\"installed\":%d,\"src\":\"%s\",\"src_path\":\"%s\","
    "\"dest\":\"%s\",\"dest_path\":\"%s\"}}\n",
    it->id,it->kind,OfferCatName(it->cat),it->title,it->blurb,
    it->price,it->is_new,it->installed,it->src,OfferOrEmpty(src),
    it->dest,dest);
  name=MStrPrint("get-%s.json",it->id);
  OfferingsWriteJson(name,json);
  Free(name);
  Free(json);
  Free(dest);
  Free(home);
  Free(src);
}

U0 OfferingsInstall(U8 *id)
{//CLI helper: install without opening the window.
  COfferItem *it=OfferFindItem(id);
  if (it && OfferInstall(it))
    "Offerings installed: %s -> %s\n",it->title,it->dest;
  else
    "Offerings: could not install %s\n",OfferOrEmpty(id);
}

#endif
