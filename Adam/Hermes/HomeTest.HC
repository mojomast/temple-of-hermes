// Guest regression for Adam/Hermes/Home.HC.
// Load Home.HC first, then include this file: "#include \"HomeTest\";".
// Writes B:/Home/hermes/HOME-TEST.TXT and prints HOME TEST DONE.

#ifndef HERMES_HOMETEST_HC
#define HERMES_HOMETEST_HC

U8 *HTAdd(U8 *buf,U8 *line)
{
  U8 *tmp=MStrPrint("%s%s\n",buf,line);
  Free(buf);
  return tmp;
}

Bool HTPre(U8 *s,U8 *pre)
{
  if (!s) return FALSE;
  return StrNCmp(s,pre,StrLen(pre))==0;
}

U0 HermesHomeTest()
{
  U8 *r,*rep,*tail,*proj;
  U8 big[301];
  I64 i,pass=0,total=0,wrote=-1;
  Bool cok=FALSE;

  rep=StrNew("HERMES HOME TEST (0.1.3)\n");

  total++;
  r=HomeInit("hermes",'B');
  if (HTPre(r,"OK ")) { pass++; rep=HTAdd(rep,"PASS b_init"); }
  else rep=HTAdd(rep,"FAIL b_init");
  if (r) Free(r);

  total++;
  r=JournalAdd("session one");
  if (HTPre(r,"OK ")) { pass++; rep=HTAdd(rep,"PASS journal_add_1"); }
  else rep=HTAdd(rep,"FAIL journal_add_1");
  if (r) Free(r);

  total++;
  r=JournalAdd("session\ttwo\nnext");
  if (HTPre(r,"OK ")) { pass++; rep=HTAdd(rep,"PASS journal_add_2"); }
  else rep=HTAdd(rep,"FAIL journal_add_2");
  if (r) Free(r);

  for (i=0;i<300;i++) big[i]='X';
  big[300]=0;
  total++;
  r=JournalAdd(big);
  if (HTPre(r,"OK ")) { pass++; rep=HTAdd(rep,"PASS journal_add_long"); }
  else rep=HTAdd(rep,"FAIL journal_add_long");
  if (r) Free(r);

  total++;
  tail=JournalTail(3);
  if (tail && StrNCmp(tail,"ERR ",4)!=0 &&
      StrIMatch("session one",tail) && StrIMatch("sessiontwo",tail))
  { pass++; rep=HTAdd(rep,"PASS journal_tail"); }
  else rep=HTAdd(rep,"FAIL journal_tail");
  if (tail) Free(tail);

  total++;
  r=ProjectSet("Temple of Hermes","Write HOME-DIR docs");
  if (HTPre(r,"OK ")) { pass++; rep=HTAdd(rep,"PASS project_set"); }
  else rep=HTAdd(rep,"FAIL project_set");
  if (r) Free(r);

  total++;
  proj=ProjectShow();
  if (proj && StrIMatch("Current: Temple of Hermes",proj) &&
      StrIMatch("Next: Write HOME-DIR docs",proj))
  { pass++; rep=HTAdd(rep,"PASS project_show"); }
  else rep=HTAdd(rep,"FAIL project_show");
  if (proj) Free(proj);

  total++;
  r=HomeInit("bad handle!",'B');
  if (HTPre(r,"ERR bad_handle")) { pass++; rep=HTAdd(rep,"PASS bad_handle"); }
  else rep=HTAdd(rep,"FAIL bad_handle");
  if (r) Free(r);
  r=HomeInit("hermes",'B');
  if (r) Free(r);

  try { cok=Let2Drv('C',FALSE)!=NULL; }
  catch { Fs->catch_except=TRUE; cok=FALSE; }
  if (!cok)
  {
    total++;
    r=HomeInit(NULL,'C');
    if (HTPre(r,"ERR ")) { pass++; rep=HTAdd(rep,"PASS no_c_error"); }
    else rep=HTAdd(rep,"FAIL no_c_error");
    if (r) Free(r);
  }
  else
  {
    r=HomeInit("hermes",'C');
    if (HTPre(r,"OK "))
    {
      Free(r);
      total++;
      r=JournalAdd("c session");
      if (HTPre(r,"OK ")) { pass++; rep=HTAdd(rep,"PASS c_journal"); }
      else rep=HTAdd(rep,"FAIL c_journal");
      if (r) Free(r);
      total++;
      r=ProjectSet("C project","C next");
      if (HTPre(r,"OK ")) { pass++; rep=HTAdd(rep,"PASS c_projects"); }
      else rep=HTAdd(rep,"FAIL c_projects");
      if (r) Free(r);
    }
    else
    {
      if (r) Free(r);
      rep=HTAdd(rep,"SKIP c_not_writable");
    }
    r=HomeInit("hermes",'B');
    if (r) Free(r);
  }

  if (pass==total)
    rep=HTAdd(rep,"HERMES HOME TEST PASS");
  else
    rep=HTAdd(rep,"HERMES HOME TEST FAIL");

  try
    wrote=FileWrite("B:/Home/hermes/HOME-TEST.TXT",rep,StrLen(rep));
  catch
  {
    Fs->catch_except=TRUE;
    wrote=0;
  }
  if (wrote!=0)
    "\nHOME TEST DONE\n";
  else
    "\nHOME TEST WRITE FAILED\n";
  Free(rep);
}

HermesHomeTest;

#endif
