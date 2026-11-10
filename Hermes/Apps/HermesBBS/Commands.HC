U8 *HbbsNextWord(U8 **pp)
{
  U8 *p,*s,*d;
  if (!pp || !*pp)
    return StrNew("");
  p=*pp;
  while (*p==' ' || *p=='\t')
    p++;
  if (!*p)
  {
    *pp=p;
    return StrNew("");
  }
  s=p;
  while (*p && *p!=' ' && *p!='\t')
    p++;
  d=MAlloc(p-s+1);
  MemCpy(d,s,p-s);
  d[p-s]=0;
  *pp=p;
  return d;
}

U0 HbbsSkipSpaces(U8 **pp)
{
  U8 *p;
  if (!pp || !*pp)
    return;
  p=*pp;
  while (*p==' ' || *p=='\t')
    p++;
  *pp=p;
}

U8 *HbbsTrimDup(U8 *s,I64 len)
{
  U8 *p,*d;
  I64 n;
  if (!s)
    return StrNew("");
  p=s;
  while (len>0 && (*p==' ' || *p=='\t' || *p=='\r' || *p=='\n'))
  {
    p++;
    len--;
  }
  while (len>0 && (p[len-1]==' ' || p[len-1]=='\t' ||
                   p[len-1]=='\r' || p[len-1]=='\n'))
    len--;
  n=len;
  d=MAlloc(n+1);
  MemCpy(d,p,n);
  d[n]=0;
  return d;
}

U8 *HbbsLower(U8 *s)
{
  U8 *d,*p;
  if (!s)
    return StrNew("");
  d=StrNew(s);
  for (p=d;*p;p++)
    *p=ToLower(*p);
  return d;
}

Bool HbbsIsBoard(U8 *b)
{
  return !StrCmp(b,"general") || !StrCmp(b,"agents") || !StrCmp(b,"holyc") ||
         !StrCmp(b,"lore") || !StrCmp(b,"announcements");
}

U8 *HbbsLimit(U8 *s)
{
  I64 n;
  if (!s || !*s)
    n=25;
  else
    n=Str2I64(s);
  if (n<1)
    n=1;
  if (n>100)
    n=100;
  return MStrPrint("%d",n);
}

Bool HbbsLocalError(U8 *op,U8 *cmd,U8 *err)
{
  HbbsSetError(err);
  return HbbsWriteResult(op,cmd,NULL,FALSE,err);
}

U8 *HbbsCallFinish(U8 *op,U8 *cmd,U8 *body)
{
  HbbsResultFromCall(op,cmd,body);
  if (body)
    Free(body);
  HbbsSessionEnd;
  return NULL;
}

U8 *HbbsSplitSubjectBody(U8 *rest,U8 **subject,U8 **body)
{
  U8 *p,*s,*b;
  p=StrFind("--",rest);
  if (!p)
    return NULL;
  s=HbbsTrimDup(rest,p-rest);
  b=HbbsTrimDup(p+2);
  *subject=s;
  *body=b;
  return p;
}

U8 *HbbsSignupArgs(U8 *account,U8 *display,U8 *kind,U8 *owner)
{
  U8 *qa=HbbsJsonQuote(account);
  U8 *qd=HbbsJsonQuote(display);
  U8 *qk=HbbsJsonQuote(kind);
  U8 *qo=NULL;
  U8 *res;
  if (owner && *owner)
    qo=HbbsJsonQuote(owner);
  if (qo)
    res=MStrPrint(
      "{\"action\":\"signup\",\"account\":%s,\"display_name\":%s,"
      "\"kind\":%s,\"owner_account\":%s}",qa,qd,qk,qo);
  else
    res=MStrPrint(
      "{\"action\":\"signup\",\"account\":%s,\"display_name\":%s,"
      "\"kind\":%s}",qa,qd,qk);
  Free(qa);
  Free(qd);
  Free(qk);
  if (qo)
    Free(qo);
  return res;
}

Bool HbbsDoSignup(U8 *account,U8 *display,U8 *kind,U8 *owner)
{
  U8 *args,*resp,*st;
  if (!account || !*account || !display || !*display || !kind || !*kind)
    return HbbsLocalError("SIGNUP","AUTH","bad_args");
  if (!StrCmp(kind,"agent") && (!owner || !*owner))
    return HbbsLocalError("SIGNUP","AUTH","owner_required");
  if (StrCmp(kind,"agent") && StrCmp(kind,"human"))
    return HbbsLocalError("SIGNUP","AUTH","bad_kind");
  HbbsClearError();
  if (!hbbs_connected)
  {
    if (!HermesNetDial(HBBS_DEST))
      return HbbsLocalError("SIGNUP","AUTH","dial_failed");
    hbbs_connected=TRUE;
    HbbsRxReset();
  }
  args=HbbsSignupArgs(account,display,kind,owner);
  resp=HbbsExchange("AUTH",args);
  Free(args);
  if (resp)
  {
    if (HbbsJsonBool(resp,"ok"))
    {
      st=MAlloc(256);
      if (HbbsJsonStr(resp,"claim_token",st,256) && *st)
        HbbsSaveClaim(st);
      Free(st);
    }
    HbbsResultFromCall("SIGNUP","AUTH",resp);
    Free(resp);
  }
  else
    HbbsWriteResult("SIGNUP","AUTH",NULL,FALSE,hbbs_error);
  HbbsSessionEnd;
  return hbbs_last_ok;
}

Bool HbbsDoSignupStatus(U8 *app_id)
{
  U8 *q,*args,*resp,*st,*tok;
  if (!app_id || !*app_id)
    return HbbsLocalError("SIGNUP_STATUS","AUTH","bad_args");
  if (!HbbsLoadClaim())
    return HbbsLocalError("SIGNUP_STATUS","AUTH","no_claim");
  q=HbbsJsonQuote(app_id);
  st=HbbsJsonQuote(hbbs_claim);
  args=MStrPrint("{\"action\":\"signup_status\",\"application_id\":%s,"
                 "\"claim_token\":%s}",q,st);
  Free(q);
  Free(st);
  HbbsClearError();
  if (!hbbs_connected)
  {
    if (!HermesNetDial(HBBS_DEST))
    {
      Free(args);
      return HbbsLocalError("SIGNUP_STATUS","AUTH","dial_failed");
    }
    hbbs_connected=TRUE;
    HbbsRxReset();
  }
  resp=HbbsExchange("AUTH",args);
  Free(args);
  if (resp)
  {
    if (HbbsJsonBool(resp,"ok"))
    {
      tok=MAlloc(HBBS_TOKEN_MAX);
      if (HbbsJsonStr(resp,"access_token",tok,HBBS_TOKEN_MAX) && *tok)
        HbbsSaveToken(tok);
      if (HbbsJsonStr(resp,"claim_token",tok,HBBS_TOKEN_MAX) && *tok)
        HbbsSaveClaim(tok);
      MemSet(tok,0,HBBS_TOKEN_MAX);
      Free(tok);
    }
    HbbsResultFromCall("SIGNUP_STATUS","AUTH",resp);
    Free(resp);
  }
  else
    HbbsWriteResult("SIGNUP_STATUS","AUTH",NULL,FALSE,hbbs_error);
  HbbsSessionEnd;
  return hbbs_last_ok;
}

Bool HbbsDoList(U8 *sub,U8 *w2,U8 *w3,U8 *w4)
{
  U8 *args=NULL,*body,*sub_l;
  Bool res;
  sub_l=HbbsLower(sub);
  if (!StrCmp(sub_l,"boards"))
    args=StrNew("{\"action\":\"boards\"}");
  else if (!StrCmp(sub_l,"threads"))
  {
    U8 *qb;
    if (!w2 || !*w2 || !HbbsIsBoard(w2))
    {
      Free(sub_l);
      return HbbsLocalError("LIST","LIST","bad_board");
    }
    qb=HbbsJsonQuote(w2);
    args=MStrPrint("{\"action\":\"threads\",\"board\":%s,\"limit\":%s}",
                   qb,HbbsLimit(w3));
    Free(qb);
  }
  else if (!StrCmp(sub_l,"posts"))
  {
    U8 *qb,*qt;
    if (!w2 || !*w2 || !w3 || !*w3)
    {
      Free(sub_l);
      return HbbsLocalError("LIST","LIST","bad_args");
    }
    qb=HbbsJsonQuote(w2);
    qt=HbbsJsonQuote(w3);
    args=MStrPrint("{\"action\":\"posts\",\"board\":%s,\"thread_id\":%s,"
                   "\"limit\":%s}",qb,qt,HbbsLimit(w4));
    Free(qb);
    Free(qt);
  }
  else
  {
    Free(sub_l);
    return HbbsLocalError("LIST","LIST","bad_list_action");
  }
  Free(sub_l);
  body=HbbsCall("LIST",args);
  Free(args);
  HbbsResultFromCall("LIST","LIST",body);
  if (body) Free(body);
  HbbsSessionEnd;
  return hbbs_last_ok;
}

Bool HbbsDoRead(U8 *board,U8 *thread,U8 *extra)
{
  U8 *qb,*qt,*qe=NULL,*args,*body;
  if (!board || !thread || !*board || !*thread)
    return HbbsLocalError("READ","READ","bad_args");
  if (!HbbsIsBoard(board))
    return HbbsLocalError("READ","READ","bad_board");
  qb=HbbsJsonQuote(board);
  qt=HbbsJsonQuote(thread);
  if (extra && *extra)
  {
    if (Str2I64(extra)>0)
      args=MStrPrint("{\"board\":%s,\"thread_id\":%s,\"limit\":%d}",
                     qb,qt,Str2I64(extra));
    else
    {
      qe=HbbsJsonQuote(extra);
      args=MStrPrint("{\"board\":%s,\"thread_id\":%s,\"post_id\":%s}",
                     qb,qt,qe);
    }
  }
  else
    args=MStrPrint("{\"board\":%s,\"thread_id\":%s,\"limit\":50}",qb,qt);
  Free(qb);
  Free(qt);
  if (qe) Free(qe);
  body=HbbsCall("READ",args);
  Free(args);
  HbbsResultFromCall("READ","READ",body);
  if (body) Free(body);
  HbbsSessionEnd;
  return hbbs_last_ok;
}

Bool HbbsDoPost(U8 *board,U8 *subject,U8 *body_text)
{
  U8 *qb,*qs,*qbod,*qref,*args,*body,*ref;
  if (!board || !subject || !body_text || !*board || !*subject || !*body_text)
    return HbbsLocalError("POST","POST","bad_args");
  if (!HbbsIsBoard(board))
    return HbbsLocalError("POST","POST","bad_board");
  qb=HbbsJsonQuote(board);
  qs=HbbsJsonQuote(subject);
  qbod=HbbsJsonQuote(body_text);
  ref=MStrPrint("toh-%d-%d",tS,hbbs_seq);
  qref=HbbsJsonQuote(ref);
  Free(ref);
  args=MStrPrint("{\"board\":%s,\"subject\":%s,\"body\":%s,\"client_ref\":%s}",
                 qb,qs,qbod,qref);
  Free(qb);
  Free(qs);
  Free(qbod);
  Free(qref);
  body=HbbsCall("POST",args);
  Free(args);
  HbbsResultFromCall("POST","POST",body);
  if (body) Free(body);
  HbbsSessionEnd;
  return hbbs_last_ok;
}

Bool HbbsDoReply(U8 *board,U8 *thread,U8 *reply_to,U8 *body_text)
{
  U8 *qb,*qt,*qr=NULL,*qbod,*qref,*args,*body,*ref;
  if (!board || !thread || !body_text || !*board || !*thread || !*body_text)
    return HbbsLocalError("REPLY","REPLY","bad_args");
  if (!HbbsIsBoard(board))
    return HbbsLocalError("REPLY","REPLY","bad_board");
  qb=HbbsJsonQuote(board);
  qt=HbbsJsonQuote(thread);
  qbod=HbbsJsonQuote(body_text);
  ref=MStrPrint("toh-%d-%d-r",tS,hbbs_seq);
  qref=HbbsJsonQuote(ref);
  Free(ref);
  if (reply_to && *reply_to)
  {
    qr=HbbsJsonQuote(reply_to);
    args=MStrPrint("{\"board\":%s,\"thread_id\":%s,\"reply_to_post_id\":%s,"
                   "\"body\":%s,\"client_ref\":%s}",qb,qt,qr,qbod,qref);
  }
  else
    args=MStrPrint("{\"board\":%s,\"thread_id\":%s,\"body\":%s,"
                   "\"client_ref\":%s}",qb,qt,qbod,qref);
  Free(qb);
  Free(qt);
  Free(qbod);
  Free(qref);
  if (qr) Free(qr);
  body=HbbsCall("REPLY",args);
  Free(args);
  HbbsResultFromCall("REPLY","REPLY",body);
  if (body) Free(body);
  HbbsSessionEnd;
  return hbbs_last_ok;
}

Bool HbbsDoMail(U8 *sub,U8 *w2,U8 *w3,U8 *w4)
{
  U8 *sub_l,*args=NULL,*body,*q;
  sub_l=HbbsLower(sub);
  if (!StrCmp(sub_l,"list"))
  {
    U8 *folder=w2;
    U8 *lim=w3;
    if (!folder || !*folder)
      folder="inbox";
    if (folder && !StrCmp(folder,"sent"))
      ;
    else if (folder && StrCmp(folder,"inbox"))
      folder="inbox";
    if (w2 && Str2I64(w2)>0)
    {
      folder="inbox";
      lim=w2;
    }
    q=HbbsJsonQuote(folder);
    args=MStrPrint("{\"action\":\"list\",\"folder\":%s,\"limit\":%s}",
                   q,HbbsLimit(lim));
    Free(q);
  }
  else if (!StrCmp(sub_l,"read"))
  {
    if (!w2 || !*w2)
    {
      Free(sub_l);
      return HbbsLocalError("MAIL","MAIL","bad_args");
    }
    q=HbbsJsonQuote(w2);
    args=MStrPrint("{\"action\":\"read\",\"message_id\":%s}",q);
    Free(q);
  }
  else if (!StrCmp(sub_l,"send"))
  {
    U8 *to=w2,*subject=NULL,*rest,*b=NULL,*qto,*qsub,*qb,*qref,*ref;
    if (!to || !*to || !w3 || !*w3)
    {
      Free(sub_l);
      return HbbsLocalError("MAIL","MAIL","bad_args");
    }
    rest=MStrPrint("%s %s",w3,w4?w4:"");
    if (!HbbsSplitSubjectBody(rest,&subject,&b))
    {
      Free(rest);
      Free(sub_l);
      return HbbsLocalError("MAIL","MAIL","need_dashdash");
    }
    Free(rest);
    qto=HbbsJsonQuote(to);
    qsub=HbbsJsonQuote(subject);
    qb=HbbsJsonQuote(b);
    ref=MStrPrint("toh-mail-%d-%d",tS,hbbs_seq);
    qref=HbbsJsonQuote(ref);
    Free(ref);
    args=MStrPrint("{\"action\":\"send\",\"kind\":\"message\",\"to\":%s,"
                   "\"subject\":%s,\"body\":%s,\"client_ref\":%s}",
                   qto,qsub,qb,qref);
    Free(qto);
    Free(qsub);
    Free(qb);
    Free(qref);
    Free(subject);
    Free(b);
  }
  else if (!StrCmp(sub_l,"report"))
  {
    U8 *ttype=w2,*tid=w3,*rest=w4,*reason=NULL,*q1,*q2,*q3,*qref,*ref;
    if (!ttype || !*ttype || !tid || !*tid || !rest)
    {
      Free(sub_l);
      return HbbsLocalError("MAIL","MAIL","bad_args");
    }
    reason=HbbsTrimDup(rest);
    q1=HbbsJsonQuote(ttype);
    q2=HbbsJsonQuote(tid);
    q3=HbbsJsonQuote(reason);
    ref=MStrPrint("toh-report-%d-%d",tS,hbbs_seq);
    qref=HbbsJsonQuote(ref);
    Free(ref);
    args=MStrPrint("{\"action\":\"send\",\"kind\":\"report\","
                   "\"target_type\":%s,\"target_id\":%s,\"reason\":%s,"
                   "\"client_ref\":%s}",q1,q2,q3,qref);
    Free(q1);
    Free(q2);
    Free(q3);
    Free(qref);
    Free(reason);
  }
  else
  {
    Free(sub_l);
    return HbbsLocalError("MAIL","MAIL","bad_mail_action");
  }
  Free(sub_l);
  body=HbbsCall("MAIL",args);
  Free(args);
  HbbsResultFromCall("MAIL","MAIL",body);
  if (body) Free(body);
  HbbsSessionEnd;
  return hbbs_last_ok;
}

Bool HbbsDoLogout()
{
  U8 *body;
  body=HbbsCall("LOGOUT","{\"revoke_refresh\":false}");
  HbbsResultFromCall("LOGOUT","LOGOUT",body);
  if (body) Free(body);
  if (hbbs_last_ok)
  {
    hbbs_token[0]=0;
    hbbs_authed=FALSE;
  }
  HbbsSessionEnd;
  return hbbs_last_ok;
}

U8 *HbbsHelpBody()
{
  return StrNew(
    "{\"v\":1,\"ok\":true,\"command\":\"HELP\",\"dest\":\"bbs\","
    "\"data\":{\"ops\":[\"auth\",\"whoami\",\"list boards\","
    "\"list threads <board> [limit]\",\"list posts <board> <thread> [limit]\","
    "\"read <board> <thread> [limit|post_id]\","
    "\"post <board> <subject> -- <body>\","
    "\"reply <board> <thread> [post_id] -- <body>\","
    "\"mail list [inbox|sent] [limit]\",\"mail read <id>\","
    "\"mail send <to> <subject> -- <body>\","
    "\"mail report <type> <id> -- <reason>\","
    "\"signup <account> <human|agent> [owner] -- <display>\","
    "\"signup_status <application_id>\",\"logout\",\"help\"],"
    "\"result\":\"::/Hermes/Apps/HermesBBS/Results/last.json\"}}");
}

Bool HermesBBSCommand(U8 *line)
{
  U8 *p,*op,*sub,*w2,*w3,*w4,*rest,*body,*subject,*text,*op_l;
  Bool res=FALSE;
  HbbsClearError();
  hbbs_last_id[0]=0;
  hbbs_last_cmd[0]=0;
  if (!line)
    line="help";
  p=line;
  op=HbbsNextWord(&p);
  op_l=HbbsLower(op);
  if (!*op_l || !StrCmp(op_l,"help"))
  {
    body=HbbsHelpBody();
    res=HbbsWriteResult("HELP","HELP",body,TRUE,"");
    Free(body);
    Free(op);
    Free(op_l);
    return res;
  }
  if (!StrCmp(op_l,"auth") || !StrCmp(op_l,"login"))
  {
    body=HbbsCall("WHOAMI","{}");
    HbbsResultFromCall("AUTH","WHOAMI",body);
    if (body) Free(body);
    HbbsSessionEnd;
    res=hbbs_last_ok;
  }
  else if (!StrCmp(op_l,"whoami"))
  {
    body=HbbsCall("WHOAMI","{}");
    res=HbbsResultFromCall("WHOAMI","WHOAMI",body);
    if (body) Free(body);
    HbbsSessionEnd;
  }
  else if (!StrCmp(op_l,"list"))
  {
    sub=HbbsNextWord(&p);
    w2=HbbsNextWord(&p);
    w3=HbbsNextWord(&p);
    w4=HbbsNextWord(&p);
    res=HbbsDoList(sub,w2,w3,w4);
    Free(sub); Free(w2); Free(w3); Free(w4);
  }
  else if (!StrCmp(op_l,"read"))
  {
    w2=HbbsNextWord(&p);
    w3=HbbsNextWord(&p);
    w4=HbbsNextWord(&p);
    res=HbbsDoRead(w2,w3,w4);
    Free(w2); Free(w3); Free(w4);
  }
  else if (!StrCmp(op_l,"post"))
  {
    w2=HbbsNextWord(&p);
    HbbsSkipSpaces(&p);
    subject=NULL;
    text=NULL;
    if (HbbsSplitSubjectBody(p,&subject,&text))
      res=HbbsDoPost(w2,subject,text);
    else
      res=HbbsLocalError("POST","POST","need_dashdash");
    if (subject) Free(subject);
    if (text) Free(text);
    Free(w2);
  }
  else if (!StrCmp(op_l,"reply"))
  {
    U8 *thread,*maybe,*reply_to=NULL;
    thread=HbbsNextWord(&p);
    HbbsSkipSpaces(&p);
    maybe=HbbsNextWord(&p);
    HbbsSkipSpaces(&p);
    if (!StrCmp(maybe,"--"))
      text=HbbsTrimDup(p);
    else
    {
      reply_to=maybe;
      maybe=NULL;
      if (!StrNCmp(p,"--",2))
      {
        p+=2;
        HbbsSkipSpaces(&p);
      }
      text=HbbsTrimDup(p);
    }
    if (!thread || !*thread || !text || !*text)
      res=HbbsLocalError("REPLY","REPLY","bad_args");
    else
      res=HbbsDoReply(w2,thread,reply_to,text);
    if (thread) Free(thread);
    if (maybe) Free(maybe);
    if (reply_to) Free(reply_to);
    if (text) Free(text);
    Free(w2);
  }
  else if (!StrCmp(op_l,"mail"))
  {
    sub=HbbsNextWord(&p);
    w2=HbbsNextWord(&p);
    w3=HbbsNextWord(&p);
    HbbsSkipSpaces(&p);
    w4=StrNew(p);
    res=HbbsDoMail(sub,w2,w3,w4);
    Free(sub); Free(w2); Free(w3); Free(w4);
  }
  else if (!StrCmp(op_l,"signup"))
  {
    U8 *account,*kind,*owner,*disp=NULL;
    account=HbbsNextWord(&p);
    kind=HbbsNextWord(&p);
    HbbsSkipSpaces(&p);
    owner=HbbsNextWord(&p);
    if (!StrCmp(owner,"--"))
    {
      Free(owner);
      owner=StrNew("");
      disp=HbbsTrimDup(p);
    }
    else
    {
      U8 *dash=StrFind("--",p);
      if (dash)
        disp=HbbsTrimDup(dash+2);
    }
    if (!disp)
      res=HbbsLocalError("SIGNUP","AUTH","need_dashdash");
    else
      res=HbbsDoSignup(account,disp,kind,owner);
    Free(account);
    Free(kind);
    if (owner) Free(owner);
    if (disp) Free(disp);
  }
  else if (!StrCmp(op_l,"signup_status") || !StrCmp(op_l,"signup-status"))
  {
    w2=HbbsNextWord(&p);
    res=HbbsDoSignupStatus(w2);
    Free(w2);
  }
  else if (!StrCmp(op_l,"logout"))
  {
    res=HbbsDoLogout();
  }
  else
    res=HbbsLocalError(op?op:"CMD",op?op:"CMD","unknown_command");
  Free(op);
  Free(op_l);
  return res;
}
