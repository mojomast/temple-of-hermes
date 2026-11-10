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
  if (path && *path)
  {
    try
      FileWrite(path,buf,StrLen(buf));
    catch
      Fs->catch_except=TRUE;
  }
}

U0 SpoonAgent(U8 *out_file=NULL)
{
  U8 *path,*home;
  CSpoon *s=CAlloc(sizeof(CSpoon));
  if (out_file && *out_file)
    path=StrNew(out_file);
  else
    path=HermesStateFile("Spoon","SpoonResult.TXT");
  SpInit(s,TRUE);
  SpAgentRun(s);
  SpWriteResult(s,path);
  "Spoon agent: caught=%d missed=%d score=%d\n",s->caught,s->missed,s->score;
  home=SpHome();
  "High score %d in %sSpoonScore.TXT\n",s->high,home;
  "Result: %s\n",path;
  Free(home);
  Free(path);
  SpFree(s);
}

#endif
