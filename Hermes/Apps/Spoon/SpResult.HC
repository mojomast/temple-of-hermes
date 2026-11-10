#ifndef SP_RESULT_HC
#define SP_RESULT_HC

U0 SpWriteResult(CSpoon *s,U8 *path)
{
  U8 buf[512];
  StrPrint(buf,
    "SpoonResult v1\n"
    "mode=agent\n"
    "caught=%d\n"
    "missed=%d\n"
    "score=%d\n"
    "tosses=%d\n"
    "high=%d\n"
    "currency=spoons\n"
    "real_money=false\n",
    s->caught,s->missed,s->score,s->tosses,s->high);
  FileWrite(path,buf,StrLen(buf));
}

U0 SpoonAgent(U8 *out_file=NULL)
{
  U8 *path;
  CSpoon *s=CAlloc(sizeof(CSpoon));
  if (out_file)
    path=StrNew(out_file);
  else
    path=StrNew("C:/Tmp/SpoonResult.TXT");
  SpInit(s,TRUE);
  SpAgentRun(s);
  SpWriteResult(s,path);
  "Spoon agent: caught=%d missed=%d score=%d\n",s->caught,s->missed,s->score;
  "High score %d in C:/Tmp/SpoonScore.TXT\n",s->high;
  "Result: %s\n",path;
  Free(path);
  SpFree(s);
}

#endif
