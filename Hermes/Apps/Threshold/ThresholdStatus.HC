U0 ThresholdStatus(U8 *out_file=NULL)
{//Agent-facing CLI: write MOTD, pinned apps and status to a file.
  U8 *buf=CAlloc(4096),*p=buf,*path,*motd;
  CDateStruct ds;
  I64 i;
  Date2Struct(&ds,Now+local_time_offset);
  motd=ThresholdMotdText();
  if (out_file && *out_file)
    path=StrNew(out_file);
  else
    path=MStrPrint("%s/ThresholdStatus.TXT",__DIR__);
  p=CatPrint(p,"THRESHOLD STATUS\n"); p+=StrLen(p);
  p=CatPrint(p,"status=ready\n"); p+=StrLen(p);
  p=CatPrint(p,"mode=human+agent\n"); p+=StrLen(p);
  p=CatPrint(p,"host=%s (fictional game-character host)\n",TH_HOST);
  p+=StrLen(p);
  p=CatPrint(p,"announcer=Southpaw\n"); p+=StrLen(p);
  p=CatPrint(p,"date=%04d-%02d-%02d\n",ds.year,ds.mon,ds.day_of_mon);
  p+=StrLen(p);
  p=CatPrint(p,"motd=%s\n",motd); p+=StrLen(p);
  p=CatPrint(p,"pinned=Chat,Codex,BBS,Dojo,Offerings\n"); p+=StrLen(p);
  p=CatPrint(p,"doors="); p+=StrLen(p);
  for (i=0;i<TH_NUM_DOORS;i++)
  {
    p=CatPrint(p,"%s",th_door_name[i]); p+=StrLen(p);
    if (i<TH_NUM_DOORS-1)
    {
      p=CatPrint(p,","); p+=StrLen(p);
    }
  }
  p=CatPrint(p,"\n"); p+=StrLen(p);
  p=CatPrint(p,"splash=%s\n",TH_ART_SPLASH); p+=StrLen(p);
  p=CatPrint(p,"header=%s\n",TH_ART_HEADER); p+=StrLen(p);
  p=CatPrint(p,"icon=%s\n",TH_ART_ICON); p+=StrLen(p);
  p=CatPrint(p,"new_line_1=NEW: Human, welcome back to the Threshold. "
    "I am Nous Girl, your fictional host.\n"); p+=StrLen(p);
  p=CatPrint(p,"new_line_2=NEW: Agent, the room is yours too. "
    "ThresholdStatus writes the state you need.\n"); p+=StrLen(p);
  p=CatPrint(p,"new_line_3=NEW: Southpaw calls the doors when you are ready.\n");
  p+=StrLen(p);
  FileWrite(path,buf,p-buf);
  "ThresholdStatus: wrote %s\n",path;
  Free(path);
  Free(buf);
}
