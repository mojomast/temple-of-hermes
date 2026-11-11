// Guest-side regression for the Hermes daemon file-error guards.
// Include/Load after Adam/Hermes/Load.HC defines the helpers:
//   #include "T:/Adam/Hermes/FileErrorsTest.HC"
// Uses dummy marker names only; no token, credential, or BBS state.

#ifndef HERMES_FILEERRORSTEST_HC
#define HERMES_FILEERRORSTEST_HC

U8 *HFAdd(U8 *buf,U8 *line)
{
  U8 *tmp=MStrPrint("%s%s\n",buf,line);
  Free(buf);
  return tmp;
}

Bool HFErr(U8 *json,U8 *code)
{
  U8 *needle=MStrPrint("\"code\":\"%s\"",code);
  Bool res=StrIMatch(needle,json)!=NULL;
  Free(needle);
  return res;
}

U0 HermesFileErrorsTest()
{
  U8 *r,*rep,*w,*data=NULL;
  Bool ok,wok;
  I64 pass=0,total=0,size=0,ech=0;

  rep=StrNew("HERMES FILE ERRORS TEST (0.1.3)\n");

  total++;
  r=HermesFileWriteJSON("push",
       "T:/Hermes/Apps/__HERMES_NO_SUCH_DIR__/marker.txt","dummy",5,&ok);
  if (!ok && HFErr(r,"missing_dir"))
  {
    pass++;
    rep=HFAdd(rep,"PASS missing_dir");
  }
  else
    rep=HFAdd(rep,"FAIL missing_dir");
  Free(r);

  total++;
  r=HermesFileWriteJSON("push",
       "T:/Hermes/Apps/Launcher/hermes-daemon-0.1.3-marker.txt","dummy",5,&ok);
  if (!ok && (HFErr(r,"read_only") || HFErr(r,"missing_dir")))
  {
    pass++;
    rep=HFAdd(rep,"PASS cd_read_only");
  }
  else
    rep=HFAdd(rep,"FAIL cd_read_only");
  Free(r);

  total++;
  r=HermesFileWriteJSON("push",
       "B:/Tmp/hermes-daemon-0.1.3-marker.txt","dummy marker",12,&ok);
  if (ok)
  {
    pass++;
    rep=HFAdd(rep,"PASS ram_write");
  }
  else
    rep=HFAdd(rep,"FAIL ram_write");
  Free(r);

  total++;
  r=HermesFileWriteJSON("push",
       "B:/Tmp/hermes-daemon-0.1.3-marker.txt","x",
       HERMES_MAX_PAYLOAD+1,&ok);
  if (!ok && HFErr(r,"too_large"))
  {
    pass++;
    rep=HFAdd(rep,"PASS too_large");
  }
  else
    rep=HFAdd(rep,"FAIL too_large");
  Free(r);

  total++;
  r=HermesFileWriteJSON("push",
       "Q:/Hermes/no-such-placement/marker.txt","dummy",5,&ok);
  if (!ok && HFErr(r,"bad_drive"))
  {
    pass++;
    rep=HFAdd(rep,"PASS bad_drive");
  }
  else
    rep=HFAdd(rep,"FAIL bad_drive");
  Free(r);

  total++;
  data=HermesFileReadSafe("B:/Tmp/hermes-daemon-0.1.3-marker.txt",&size,&ech);
  if (data && size==12)
  {
    pass++;
    rep=HFAdd(rep,"PASS ram_readback");
  }
  else
    rep=HFAdd(rep,"FAIL ram_readback");
  if (data)
    Free(data);

  if (pass==total)
    rep=HFAdd(rep,"HERMES FILE ERRORS TEST PASS");
  else
    rep=HFAdd(rep,"HERMES FILE ERRORS TEST FAIL");

  w=HermesFileWriteJSON("guest_test",
       "B:/Tmp/HERMES_FILE_ERRORS_RESULT.TXT",rep,StrLen(rep),&wok);
  Free(w);
  Free(rep);
}

HermesFileErrorsTest;

#endif
