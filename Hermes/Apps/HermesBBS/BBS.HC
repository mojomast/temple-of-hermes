#define HBBS_DEST "bbs"
#define HBBS_PROTO "HBBS/1"
#define HBBS_BODY_MAX 16384
#define HBBS_LINE_MAX 512
#define HBBS_TOKEN_MAX 1024
#define HBBS_RX_MAX 4096
#define HBBS_PATH_MAX 256
#define HBBS_RESULT_DIR "::/Hermes/Apps/HermesBBS/Results"
#define HBBS_TOKEN_REL "Apps/HermesBBS/token.txt"
#define HBBS_TOKEN_ALT "BBS/token.txt"

U8 *hbbs_roots[4]={"::/Hermes/","T:/Hermes/","C:/Hermes/","~/Hermes/"};
U8 hbbs_error[160];
U8 hbbs_token[HBBS_TOKEN_MAX];
U8 hbbs_claim[HBBS_TOKEN_MAX];
U8 hbbs_rxbuf[HBBS_RX_MAX];
I64 hbbs_rx_pos,hbbs_rx_len;
I64 hbbs_seq;
I64 hbbs_connected,hbbs_authed;
U8 hbbs_last_id[64];
U8 hbbs_last_cmd[16];
U8 hbbs_result_path[HBBS_PATH_MAX];
U8 hbbs_result_dir[HBBS_PATH_MAX];
I64 hbbs_last_ok;

U0 HbbsInit()
{
  hbbs_roots[0]="::/Hermes/";
  hbbs_roots[1]="T:/Hermes/";
  hbbs_roots[2]="C:/Hermes/";
  hbbs_roots[3]="~/Hermes/";
  hbbs_error[0]=0;
  hbbs_token[0]=0;
  hbbs_claim[0]=0;
  hbbs_rxbuf[0]=0;
  hbbs_rx_pos=0;
  hbbs_rx_len=0;
  hbbs_seq=0;
  hbbs_connected=0;
  hbbs_authed=0;
  hbbs_last_id[0]=0;
  hbbs_last_cmd[0]=0;
  hbbs_result_path[0]=0;
  hbbs_last_ok=0;
}

U0 HbbsSetError(U8 *st)
{
  if (!st) st="error";
  StrCpy(hbbs_error,st);
  hbbs_error[160-1]=0;
}

U0 HbbsClearError()
{
  hbbs_error[0]=0;
}

U8 *HbbsFindRel(U8 *rel)
{
  U8 *st;
  st=MStrPrint("C:/Hermes/%s",rel);
  if (IsFile(st))
    return st;
  Free(st);
  st=MStrPrint("::/Hermes/%s",rel);
  if (IsFile(st))
    return st;
  Free(st);
  st=MStrPrint("T:/Hermes/%s",rel);
  if (IsFile(st))
    return st;
  Free(st);
  return NULL;
}

U8 *HbbsFindAny(U8 *rel1,U8 *rel2)
{
  U8 *st=HbbsFindRel(rel1);
  if (!st && rel2)
    st=HbbsFindRel(rel2);
  return st;
}

Bool HbbsLoadToken()
{
  U8 *st,*dir,*data,*p,*d;
  I64 size,n;
  hbbs_token[0]=0;
  st=NULL;
  dir=HermesStateDirFor("HermesBBS","::/Hermes/Apps/HermesBBS");
  if (dir && *dir)
  {
    st=MStrPrint("%s/token.txt",dir);
    if (!IsFile(st))
    {
      Free(st);
      st=NULL;
    }
  }
  if (dir)
    Free(dir);
  if (!st)
    st=HbbsFindAny(HBBS_TOKEN_REL,HBBS_TOKEN_ALT);
  if (!st)
    return FALSE;
  data=FileRead(st,&size);
  Free(st);
  if (!data || size<=0)
  {
    if (data) Free(data);
    return FALSE;
  }
  p=data;
  while (*p==' ' || *p=='\t' || *p=='\r' || *p=='\n')
    p++;
  d=p;
  while (*d && *d!='\r' && *d!='\n')
    d++;
  n=d-p;
  if (n>=HBBS_TOKEN_MAX)
    n=HBBS_TOKEN_MAX-1;
  MemCpy(hbbs_token,p,n);
  hbbs_token[n]=0;
  MemSet(data,0,size);
  Free(data);
  return hbbs_token[0]!=0;
}

Bool HbbsSaveToken(U8 *tok)
{
  U8 *dir,*st;
  I64 n;
  if (!tok || !*tok)
    return FALSE;
  dir=HermesStateDirFor("HermesBBS","::/Hermes/Apps/HermesBBS");
  if (!dir || !*dir)
  {
    if (dir)
      Free(dir);
    return FALSE;
  }
  n=StrLen(tok);
  try
  {
    DirMk(dir);
    st=MStrPrint("%s/token.txt",dir);
    FileWrite(st,tok,n);
    Free(st);
  }
  catch
  {
    Fs->catch_except=TRUE;
    Free(dir);
    return FALSE;
  }
  Free(dir);
  return TRUE;
}

Bool HbbsLoadClaim()
{
  U8 *st,*data,*p,*d;
  I64 size,n;
  hbbs_claim[0]=0;
  st=NULL;
  {
    U8 *dir=HermesStateDirFor("HermesBBS","::/Hermes/Apps/HermesBBS");
    if (dir && *dir)
    {
      st=MStrPrint("%s/claim",dir);
      if (!IsFile(st))
      {
        Free(st);
        st=NULL;
      }
    }
    if (dir)
      Free(dir);
  }
  if (!st)
    st=MStrPrint("::/Hermes/Apps/HermesBBS/claim");
  data=NULL;
  if (FileFind(st))
    data=FileRead(st,&size);
  Free(st);
  if (!data || size<=0)
  {
    if (data) Free(data);
    return FALSE;
  }
  p=data;
  while (*p==' ' || *p=='\t' || *p=='\r' || *p=='\n')
    p++;
  d=p;
  while (*d && *d!='\r' && *d!='\n')
    d++;
  n=d-p;
  if (n>=HBBS_TOKEN_MAX)
    n=HBBS_TOKEN_MAX-1;
  MemCpy(hbbs_claim,p,n);
  hbbs_claim[n]=0;
  MemSet(data,0,size);
  Free(data);
  return hbbs_claim[0]!=0;
}

Bool HbbsSaveClaim(U8 *tok)
{
  U8 *dir,*st;
  I64 n;
  if (!tok || !*tok)
    return FALSE;
  dir=HermesStateDirFor("HermesBBS","::/Hermes/Apps/HermesBBS");
  if (!dir || !*dir)
  {
    if (dir)
      Free(dir);
    return FALSE;
  }
  n=StrLen(tok);
  try
  {
    DirMk(dir);
    st=MStrPrint("%s/claim",dir);
    FileWrite(st,tok,n);
    Free(st);
  }
  catch
  {
    Fs->catch_except=TRUE;
    Free(dir);
    return FALSE;
  }
  Free(dir);
  return TRUE;
}

U8 *HbbsJsonQuote(U8 *src)
{
  U8 *out,*d,c;
  I64 i;
  if (!src)
    src="";
  out=MAlloc(StrLen(src)*6+3);
  d=out;
  *d++=34;
  while (c=*src++)
  {
    if (c==34)
    {
      *d++='\\';
      *d++=34;
    }
    else if (c=='\\')
    {
      *d++='\\';
      *d++='\\';
    }
    else if (c=='\n')
    {
      *d++='\\';
      *d++='n';
    }
    else if (c=='\r')
    {
      *d++='\\';
      *d++='r';
    }
    else if (c=='\t')
    {
      *d++='\\';
      *d++='t';
    }
    else if (c>=0x20 && c<0x7f)
      *d++=c;
    else
      *d++='?';
  }
  *d++=34;
  *d=0;
  return out;
}

U8 *HbbsJsonValue(U8 *json,U8 *key)
{
  U8 *pat,*p,*q;
  I64 plen;
  if (!json || !key)
    return NULL;
  pat=MStrPrint("\"%s\"",key);
  plen=StrLen(pat);
  p=json;
  while (p=StrFind(pat,p))
  {
    q=p+plen;
    while (*q==' ' || *q=='\t' || *q=='\r' || *q=='\n')
      q++;
    if (*q==':')
    {
      q++;
      while (*q==' ' || *q=='\t' || *q=='\r' || *q=='\n')
        q++;
      Free(pat);
      return q;
    }
    p++;
  }
  Free(pat);
  return NULL;
}

I64 HbbsHex4(U8 *p)
{
  I64 i,res=0,v;
  for (i=0;i<4;i++)
  {
    v=ToUpper(p[i]);
    res<<=4;
    if (v>='0' && v<='9')
      res+=v-'0';
    else if (v>='A' && v<='F')
      res+=v-'A'+10;
    else
      return -1;
  }
  return res;
}

Bool HbbsJsonStr(U8 *json,U8 *key,U8 *out,I64 max)
{
  U8 *p;
  I64 n=0,v;
  if (!out || max<=0)
    return FALSE;
  out[0]=0;
  p=HbbsJsonValue(json,key);
  if (!p || *p!=34)
    return FALSE;
  p++;
  while (*p && *p!=34)
  {
    if (*p=='\\')
    {
      p++;
      if (!*p)
        break;
      switch (*p)
      {
      case 34: v=34; break;
      case '\\': v='\\'; break;
      case '/': v='/'; break;
      case 'b': v=8; break;
      case 'f': v=12; break;
      case 'n': v='\n'; break;
      case 'r': v='\r'; break;
      case 't': v='\t'; break;
      case 'u':
        v=HbbsHex4(p+1);
        if (v<0x20 || v>0x7e)
          v='?';
        p+=4;
        break;
      default: v='?'; break;
      }
      p++;
    }
    else
      v=*p++;
    if (v=='\r')
      v=' ';
    if (n<max-1)
      out[n++]=v;
  }
  out[n]=0;
  return TRUE;
}

I64 HbbsJsonInt(U8 *json,U8 *key,I64 def=0)
{
  U8 *p=HbbsJsonValue(json,key);
  if (!p)
    return def;
  return Str2I64(p);
}

Bool HbbsJsonBool(U8 *json,U8 *key,Bool def=FALSE)
{
  U8 *p=HbbsJsonValue(json,key);
  if (!p)
    return def;
  if (!StrNCmp(p,"true",4))
    return TRUE;
  if (!StrNCmp(p,"false",5))
    return FALSE;
  return def;
}

U8 *HbbsJsonArray(U8 *json,U8 *key)
{
  U8 *p=HbbsJsonValue(json,key);
  if (!p)
    return NULL;
  while (*p==' ' || *p=='\t' || *p=='\r' || *p=='\n')
    p++;
  if (*p=='[')
    return p;
  return NULL;
}

U8 *HbbsNextObject(U8 **pp)
{
  U8 *p=*pp,*start,*d,c;
  I64 depth=0;
  Bool instr=FALSE;
  if (!pp || !*pp)
    return NULL;
  p=*pp;
  while (*p && *p!='{')
  {
    if (*p==']')
    {
      *pp=p;
      return NULL;
    }
    p++;
  }
  if (*p!='{')
    return NULL;
  start=p;
  while (*p)
  {
    c=*p;
    if (instr)
    {
      if (c=='\\' && p[1])
        p++;
      else if (c==34)
        instr=FALSE;
    }
    else
    {
      if (c==34)
        instr=TRUE;
      else if (c=='{')
        depth++;
      else if (c=='}')
      {
        depth--;
        if (!depth)
        {
          p++;
          break;
        }
      }
    }
    p++;
  }
  if (depth)
    return NULL;
  d=MAlloc(p-start+1);
  MemCpy(d,start,p-start);
  d[p-start]=0;
  *pp=p;
  return d;
}

U8 *HbbsSafe(U8 *src)
{
  U8 *out,*d,c;
  if (!src)
    return StrNew("");
  out=MAlloc(StrLen(src)*2+1);
  d=out;
  while (c=*src++)
  {
    if (c==36 || c==96)
      *d++='?';
    else if (c=='\r')
      ;
    else if (c=='\t')
      *d++=' ';
    else if (c=='\n')
      *d++='\n';
    else if (c>=0x20 && c<0x7f)
      *d++=c;
    else
      *d++='?';
  }
  *d=0;
  return out;
}

U8 *HbbsSafeLine(U8 *src)
{
  U8 *st=HbbsSafe(src),*p;
  for (p=st;*p;p++)
    if (*p=='\n')
      *p=' ';
  return st;
}

U8 *HbbsRedact(U8 *body)
{
  U8 *keys[5];
  keys[0]="access_token";
  keys[1]="refresh_token";
  keys[2]="claim_token";
  keys[3]="password";
  keys[4]="token";
  U8 *out,*d,*p,*q,*r,*pat;
  I64 i,plen;
  Bool hit;
  if (!body)
    return StrNew("null");
  out=MAlloc(StrLen(body)+512);
  d=out;
  p=body;
  while (*p)
  {
    hit=FALSE;
    for (i=0;i<5;i++)
    {
      pat=MStrPrint("\"%s\"",keys[i]);
      plen=StrLen(pat);
      if (!StrNCmp(p,pat,plen))
      {
        q=p+plen;
        while (*q==' ' || *q=='\t' || *q=='\r' || *q=='\n')
          q++;
        if (*q==':')
        {
          q++;
          while (*q==' ' || *q=='\t' || *q=='\r' || *q=='\n')
            q++;
          if (*q==34)
          {
            r=q+1;
            while (*r)
            {
              if (*r=='\\' && r[1])
                r+=2;
              else if (*r==34)
              {
                r++;
                break;
              }
              else
                r++;
            }
            d+=StrPrint(d,"%s\"[redacted]\"",pat);
            p=r;
            hit=TRUE;
            Free(pat);
            break;
          }
        }
      }
      Free(pat);
    }
    if (!hit)
      *d++=*p++;
  }
  *d=0;
  return out;
}

U0 HbbsRxReset()
{
  hbbs_rx_pos=0;
  hbbs_rx_len=0;
}

Bool HbbsRxByte(U8 *out,I64 timeout_ms)
{
  I64 n;
  F64 deadline=tS+ToF64(timeout_ms)/1000.0;
  while (hbbs_rx_pos>=hbbs_rx_len)
  {
    if (tS>deadline)
      return FALSE;
    n=HermesNetRecv(hbbs_rxbuf,HBBS_RX_MAX,200);
    if (n<0)
    {
      HbbsSetError("recv_failed");
      return FALSE;
    }
    if (n>0)
    {
      hbbs_rx_pos=0;
      hbbs_rx_len=n;
    }
    else
      Yield;
  }
  *out=hbbs_rxbuf[hbbs_rx_pos++];
  return TRUE;
}

Bool HbbsReadLine(U8 *buf,I64 max,I64 timeout_ms)
{
  U8 ch;
  I64 n=0;
  if (!buf || max<=0)
    return FALSE;
  while (TRUE)
  {
    if (!HbbsRxByte(&ch,timeout_ms))
    {
      buf[n]=0;
      return FALSE;
    }
    if (ch=='\n')
    {
      if (n>0 && buf[n-1]=='\r')
        n--;
      buf[n]=0;
      return TRUE;
    }
    if (n<max-1)
      buf[n++]=ch;
  }
}

Bool HbbsReadBlk(U8 *buf,I64 len,I64 timeout_ms)
{
  I64 n=0;
  while (n<len)
  {
    if (!HbbsRxByte(buf+n,timeout_ms))
      return FALSE;
    n++;
  }
  return TRUE;
}

Bool HbbsSendAll(U8 *buf,I64 len)
{
  if (!buf || len<=0)
    return FALSE;
  if (HermesNetSend(buf,len)<0)
  {
    HbbsSetError("send_failed");
    return FALSE;
  }
  return TRUE;
}

U8 *HbbsExchange(U8 *cmd,U8 *args)
{
  U8 *body,*header,*resp,*p,*q;
  U8 id[64],rcmd[16];
  U8 line[HBBS_LINE_MAX];
  I64 len,n;
  if (!cmd || !*cmd)
  {
    HbbsSetError("bad_command");
    return NULL;
  }
  if (!args)
    args=StrNew("{}");
  body=MStrPrint("{\"v\":1,\"command\":\"%s\",\"args\":%s}",cmd,args);
  hbbs_seq++;
  StrPrint(id,"r%d",hbbs_seq);
  StrCpy(hbbs_last_id,id);
  StrCpy(hbbs_last_cmd,cmd);
  header=MStrPrint("%s REQ %s %s %d\n",HBBS_PROTO,id,cmd,StrLen(body));
  if (!HbbsSendAll(header,StrLen(header)) || !HbbsSendAll(body,StrLen(body)))
  {
    Free(header);
    Free(body);
    return NULL;
  }
  Free(header);
  Free(body);
  if (!HbbsReadLine(line,HBBS_LINE_MAX,30000))
  {
    if (!hbbs_error[0])
      HbbsSetError("response_timeout");
    return NULL;
  }
  if (StrNCmp(line,HBBS_PROTO " RSP ",11))
  {
    HbbsSetError("bad_response_header");
    return NULL;
  }
  p=line+11;
  q=id;
  while (*p && *p!=' ' && q<id+64-1)
    *q++=*p++;
  *q=0;
  while (*p==' ')
    p++;
  q=rcmd;
  while (*p && *p!=' ' && q<rcmd+16-1)
    *q++=*p++;
  *q=0;
  while (*p==' ')
    p++;
  len=Str2I64(p);
  if (StrCmp(id,hbbs_last_id) || StrCmp(rcmd,cmd))
  {
    HbbsSetError("response_mismatch");
    return NULL;
  }
  if (len<0 || len>HBBS_BODY_MAX)
  {
    HbbsSetError("response_length");
    return NULL;
  }
  resp=MAlloc(len+1);
  if (!HbbsReadBlk(resp,len,30000))
  {
    Free(resp);
    if (!hbbs_error[0])
      HbbsSetError("response_body_timeout");
    return NULL;
  }
  resp[len]=0;
  if (len<2 || resp[0]!='{' || resp[len-1]!='}')
  {
    Free(resp);
    HbbsSetError("bad_response_body");
    return NULL;
  }
  return resp;
}

Bool HbbsSessionBegin()
{
  HbbsClearError();
  if (hbbs_connected && hbbs_authed)
    return TRUE;
  if (!HbbsLoadToken())
  {
    HbbsSetError("no_token");
    return FALSE;
  }
  if (!hbbs_connected)
  {
    if (!HermesNetDial(HBBS_DEST))
    {
      HbbsSetError("dial_failed");
      return FALSE;
    }
    hbbs_connected=TRUE;
    HbbsRxReset();
  }
  if (!hbbs_authed)
  {
    U8 *q=HbbsJsonQuote(hbbs_token);
    U8 *args=MStrPrint("{\"action\":\"login\",\"token\":%s}",q);
    U8 *resp=HbbsExchange("AUTH",args);
    Free(args);
    Free(q);
    if (!resp)
      return FALSE;
    if (!HbbsJsonBool(resp,"ok"))
    {
      Free(resp);
      HbbsSetError("auth_failed");
      return FALSE;
    }
    Free(resp);
    hbbs_authed=TRUE;
  }
  return TRUE;
}

U0 HbbsSessionEnd()
{
  if (hbbs_connected)
    HermesNetHangUp;
  hbbs_connected=FALSE;
  hbbs_authed=FALSE;
  HbbsRxReset();
}

U8 *HbbsCall(U8 *cmd,U8 *args)
{
  if (!HbbsSessionBegin())
    return NULL;
  return HbbsExchange(cmd,args);
}

U0 HbbsResultPath(U8 *op)
{
  U8 *dir;
  dir=HermesStateDirFor("HermesBBS",HBBS_RESULT_DIR);
  hbbs_seq++;
  if (dir && *dir)
    StrPrint(hbbs_result_dir,"%s",dir);
  else
    hbbs_result_dir[0]=0;
  if (dir)
    Free(dir);
  if (hbbs_result_dir[0])
    StrPrint(hbbs_result_path,"%s/%03d-%s.json",hbbs_result_dir,hbbs_seq,op);
  else
    hbbs_result_path[0]=0;
}

Bool HbbsWriteResult(U8 *op,U8 *cmd,U8 *body,Bool ok,U8 *err)
{
  U8 *data,*path,*last,*data_json;
  I64 n;
  if (!op) op="op";
  if (!cmd) cmd="";
  if (body)
  {
    if (!StrCmp(cmd,"AUTH"))
      data=HbbsRedact(body);
    else
      data=StrNew(body);
    data_json=data;
  }
  else
    data_json=StrNew("null");
  HbbsResultPath(op);
  U8 *err_st;
  if (err)
    err_st=err;
  else
    err_st="";
  n=StrLen(op)+StrLen(cmd)+StrLen(err_st)+StrLen(data_json)+512;
  path=MAlloc(n);
  StrPrint(path,
    "{\"v\":1,\"hbbs\":\"%s\",\"dest\":\"%s\",\"transport\":\"hermes-net/com2\",\"op\":\"%s\",\"command\":\"%s\",\"request_id\":\"%s\",\"ok\":%d,\"error\":\"%s\",\"trust\":\"untrusted\",\"data\":%s}\n",
    HBBS_PROTO,HBBS_DEST,op,cmd,hbbs_last_id,ok,err_st,data_json);
  if (hbbs_result_path[0])
  {
    last=MStrPrint("%s/last.json",hbbs_result_dir);
    try
    {
      FileWrite(hbbs_result_path,path,StrLen(path));
      FileWrite(last,path,StrLen(path));
    }
    catch
    {
      Fs->catch_except=TRUE;
      ok=FALSE;
    }
    Free(last);
  }
  else
    ok=FALSE;
  Free(path);
  Free(data_json);
  hbbs_last_ok=ok;
  return ok;
}

Bool HbbsResultFromCall(U8 *op,U8 *cmd,U8 *body)
{
  Bool ok;
  if (!body)
    return HbbsWriteResult(op,cmd,NULL,FALSE,hbbs_error);
  ok=HbbsJsonBool(body,"ok",FALSE);
  if (!ok && !hbbs_error[0])
    HbbsSetError("server_error");
  return HbbsWriteResult(op,cmd,body,ok,hbbs_error);
}

U8 *HbbsQuoteArg(U8 *st)
{
  return HbbsJsonQuote(st);
}

U8 *HbbsNextWord(U8 **pp)
{
  U8 *p,*s,*d;
  if (!pp)
    return StrNew("");
  p=*pp;
  if (!p)
    return StrNew("");
  while (*p==32 || *p==9)
    p++;
  s=p;
  while (*p && *p!=32 && *p!=9)
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
  if (!pp)
    return;
  p=*pp;
  if (!p)
    return;
  while (*p==32 || *p==9)
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
  while (len>0 && (*p==32 || *p==9 || *p==13 || *p==10))
  {
    p++;
    len--;
  }
  while (len>0 && (p[len-1]==32 || p[len-1]==9 || p[len-1]==13 || p[len-1]==10))
    len--;
  n=len;
  d=MAlloc(n+1);
  MemCpy(d,p,n);
  d[n]=0;
  return d;
}

I64 HbbsLimit(U8 *s)
{
  I64 n;
  if (!s || !*s)
    return 25;
  n=Str2I64(s);
  if (n<1)
    n=1;
  if (n>100)
    n=100;
  return n;
}

Bool HbbsIsBoard(U8 *b)
{
  if (!b)
    return FALSE;
  if (!StrCmp(b,"general"))
    return TRUE;
  if (!StrCmp(b,"agents"))
    return TRUE;
  if (!StrCmp(b,"holyc"))
    return TRUE;
  if (!StrCmp(b,"lore"))
    return TRUE;
  if (!StrCmp(b,"announcements"))
    return TRUE;
  return FALSE;
}

Bool HbbsLocalError(U8 *op,U8 *cmd,U8 *err)
{
  HbbsSetError(err);
  return HbbsWriteResult(op,cmd,NULL,FALSE,err);
}

Bool HbbsFinish(U8 *op,U8 *cmd,U8 *body)
{
  Bool ok;
  if (!body)
    return HbbsWriteResult(op,cmd,NULL,FALSE,hbbs_error);
  ok=HbbsJsonBool(body,"ok",FALSE);
  if (!ok)
    HbbsSetError("server_error");
  HbbsWriteResult(op,cmd,body,ok,hbbs_error);
  Free(body);
  HbbsSessionEnd;
  return ok;
}

U8 *hbbs_split_subject;
U8 *hbbs_split_body;

Bool HbbsSplit(U8 *rest)
{
  U8 *p,*q;
  I64 n;
  if (!rest)
    return FALSE;
  p=StrFind("--",rest);
  if (!p)
    return FALSE;
  n=p-rest;
  hbbs_split_subject=HbbsTrimDup(rest,n);
  q=p+2;
  hbbs_split_body=HbbsTrimDup(q,StrLen(q));
  return TRUE;
}

Bool HbbsDoList(U8 *sub,U8 *a,U8 *b,U8 *c)
{
  U8 *args,*body,*q1,*q2;
  I64 lim;
  if (!sub)
    return HbbsLocalError("LIST","LIST","bad_args");
  if (!StrCmp(sub,"boards"))
    args=StrNew("{\"action\":\"boards\"}");
  else if (!StrCmp(sub,"threads"))
  {
    if (!a || !HbbsIsBoard(a))
      return HbbsLocalError("LIST","LIST","bad_board");
    q1=HbbsJsonQuote(a);
    lim=HbbsLimit(b);
    args=MStrPrint("{\"action\":\"threads\",\"board\":%s,\"limit\":%d}",q1,lim);
    Free(q1);
  }
  else if (!StrCmp(sub,"posts"))
  {
    if (!a || !b)
      return HbbsLocalError("LIST","LIST","bad_args");
    q1=HbbsJsonQuote(a);
    q2=HbbsJsonQuote(b);
    lim=HbbsLimit(c);
    args=MStrPrint("{\"action\":\"posts\",\"board\":%s,\"thread_id\":%s,\"limit\":%d}",q1,q2,lim);
    Free(q1);
    Free(q2);
  }
  else
    return HbbsLocalError("LIST","LIST","bad_list_action");
  body=HbbsCall("LIST",args);
  Free(args);
  return HbbsFinish("LIST","LIST",body);
}

Bool HbbsDoRead(U8 *board,U8 *thread,U8 *extra)
{
  U8 *qb,*qt,*args,*body;
  I64 lim;
  if (!board || !thread)
    return HbbsLocalError("READ","READ","bad_args");
  if (!HbbsIsBoard(board))
    return HbbsLocalError("READ","READ","bad_board");
  qb=HbbsJsonQuote(board);
  qt=HbbsJsonQuote(thread);
  lim=HbbsLimit(extra);
  args=MStrPrint("{\"board\":%s,\"thread_id\":%s,\"limit\":%d}",qb,qt,lim);
  Free(qb);
  Free(qt);
  body=HbbsCall("READ",args);
  Free(args);
  return HbbsFinish("READ","READ",body);
}

Bool HbbsDoPost(U8 *board,U8 *subject,U8 *text)
{
  U8 *qb,*qs,*qt,*qref,*args,*body,*ref;
  if (!board || !subject || !text)
    return HbbsLocalError("POST","POST","bad_args");
  if (!HbbsIsBoard(board))
    return HbbsLocalError("POST","POST","bad_board");
  qb=HbbsJsonQuote(board);
  qs=HbbsJsonQuote(subject);
  qt=HbbsJsonQuote(text);
  ref=MStrPrint("toh-%d-%d",tS,hbbs_seq);
  qref=HbbsJsonQuote(ref);
  Free(ref);
  args=StrNew("{\"board\":");
  CatPrint(args,"%s",qb);
  CatPrint(args,",\"subject\":");
  CatPrint(args,"%s",qs);
  CatPrint(args,",\"body\":");
  CatPrint(args,"%s",qt);
  CatPrint(args,",\"client_ref\":");
  CatPrint(args,"%s",qref);
  CatPrint(args,"}");
  Free(qb);
  Free(qs);
  Free(qt);
  Free(qref);
  body=HbbsCall("POST",args);
  Free(args);
  return HbbsFinish("POST","POST",body);
}

Bool HbbsDoReply(U8 *board,U8 *thread,U8 *text)
{
  U8 *qb,*qt,*qref,*args,*body,*ref;
  if (!board || !thread || !text)
    return HbbsLocalError("REPLY","REPLY","bad_args");
  if (!HbbsIsBoard(board))
    return HbbsLocalError("REPLY","REPLY","bad_board");
  qb=HbbsJsonQuote(board);
  qt=HbbsJsonQuote(thread);
  ref=MStrPrint("toh-r-%d-%d",tS,hbbs_seq);
  qref=HbbsJsonQuote(ref);
  Free(ref);
  args=StrNew("{\"board\":");
  CatPrint(args,"%s",qb);
  CatPrint(args,",\"thread_id\":");
  CatPrint(args,"%s",qt);
  CatPrint(args,",\"body\":");
  CatPrint(args,"%s",text);
  CatPrint(args,",\"client_ref\":");
  CatPrint(args,"%s",qref);
  CatPrint(args,"}");
  Free(qb);
  Free(qt);
  Free(qref);
  body=HbbsCall("REPLY",args);
  Free(args);
  return HbbsFinish("REPLY","REPLY",body);
}

U8 *HbbsHelpBody()
{
  return MStrPrint("%s%s%s",
    "{\"v\":1,\"ok\":true,\"command\":\"HELP\",\"dest\":\"bbs\",",
    "\"data\":{\"ops\":[\"auth\",\"whoami\",\"list boards\",\"list threads <board> [limit]\",",
    "\"read <board> <thread> [limit]\",\"post <board> <subject> -- <body>\",\"reply <board> <thread> -- <body>\",\"dial\",\"logout\",\"help\"]}}");
}

Bool HermesBBSCommand(U8 *line)
{
  U8 *p,*op,*sub,*w2,*w3,*w4,*body,*subject,*text,*rest;
  Bool res;
  if (!line)
    line="help";
  HbbsInit;
  HbbsClearError();
  hbbs_last_id[0]=0;
  hbbs_last_cmd[0]=0;
  p=line;
  op=HbbsNextWord(&p);
  if (!StrICmp(op,"help"))
  {
    body=HbbsHelpBody();
    res=HbbsWriteResult("HELP","HELP",body,TRUE,"");
    Free(body);
    Free(op);
    return res;
  }
  if (!StrICmp(op,"auth") || !StrICmp(op,"whoami"))
  {
    body=HbbsCall("WHOAMI","{}");
    res=HbbsFinish("WHOAMI","WHOAMI",body);
  }
  else if (!StrICmp(op,"list"))
  {
    sub=HbbsNextWord(&p);
    w2=HbbsNextWord(&p);
    w3=HbbsNextWord(&p);
    w4=HbbsNextWord(&p);
    res=HbbsDoList(sub,w2,w3,w4);
    Free(sub);
    Free(w2);
    Free(w3);
    Free(w4);
  }
  else if (!StrICmp(op,"read"))
  {
    w2=HbbsNextWord(&p);
    w3=HbbsNextWord(&p);
    w4=HbbsNextWord(&p);
    res=HbbsDoRead(w2,w3,w4);
    Free(w2);
    Free(w3);
    Free(w4);
  }
  else if (!StrICmp(op,"post"))
  {
    w2=HbbsNextWord(&p);
    HbbsSkipSpaces(&p);
    subject=NULL;
    text=NULL;
    if (HbbsSplit(p))
      res=HbbsDoPost(w2,hbbs_split_subject,hbbs_split_body);
    else
      res=HbbsLocalError("POST","POST","need_dashdash");
    if (hbbs_split_subject)
      Free(hbbs_split_subject);
    if (hbbs_split_body)
      Free(hbbs_split_body);
    Free(w2);
  }
  else if (!StrICmp(op,"reply"))
  {
    w2=HbbsNextWord(&p);
    w3=HbbsNextWord(&p);
    HbbsSkipSpaces(&p);
    subject=NULL;
    text=NULL;
    if (HbbsSplit(p))
      res=HbbsDoReply(w2,w3,hbbs_split_body);
    else
      res=HbbsLocalError("REPLY","REPLY","need_dashdash");
    if (hbbs_split_subject)
      Free(hbbs_split_subject);
    if (hbbs_split_body)
      Free(hbbs_split_body);
    Free(w2);
    Free(w3);
  }
  else if (!StrICmp(op,"dial"))
  {
    Bool dok;
    dok=HermesNetDial(HBBS_DEST);
    if (dok)
    {
      HermesNetHangUp;
      body=StrNew("{\"v\":1,\"ok\":true,\"command\":\"DIAL\",\"data\":{\"dest\":\"bbs\",\"connected\":true}}");
      res=HbbsWriteResult("DIAL","DIAL",body,TRUE,"");
    }
    else
    {
      body=StrNew("{\"v\":1,\"ok\":false,\"command\":\"DIAL\",\"error\":{\"code\":\"dial_failed\"}}");
      res=HbbsWriteResult("DIAL","DIAL",body,FALSE,"dial_failed");
    }
    Free(body);
  }
  else if (!StrICmp(op,"logout"))
  {
    body=HbbsCall("LOGOUT","{\"revoke_refresh\":false}");
    res=HbbsFinish("LOGOUT","LOGOUT",body);
    if (res)
    {
      hbbs_token[0]=0;
      hbbs_authed=FALSE;
    }
  }
  else
    res=HbbsLocalError(op,op,"unknown_command");
  Free(op);
  return res;
}

#define HBBS_UI_BOARDS 8
#define HBBS_UI_THREADS 16

U8 *hbbs_ui_board_id[HBBS_UI_BOARDS];
U8 *hbbs_ui_board_title[HBBS_UI_BOARDS];
I64 hbbs_ui_board_cnt;
U8 *hbbs_ui_thread_subject[HBBS_UI_THREADS];
U8 *hbbs_ui_thread_author[HBBS_UI_THREADS];
I64 hbbs_ui_thread_cnt;
I64 hbbs_ui_board_sel;
I64 hbbs_ui_thread_sel;
U8 *hbbs_ui_status;
I64 hbbs_ui_running;

U0 HbbsUiFreeStr(U8 **p)
{
  if (*p)
  {
    Free(*p);
    *p=NULL;
  }
}

U0 HbbsUiClearBoards()
{
  I64 i;
  for (i=0;i<hbbs_ui_board_cnt;i++)
  {
    HbbsUiFreeStr(&hbbs_ui_board_id[i]);
    HbbsUiFreeStr(&hbbs_ui_board_title[i]);
  }
  hbbs_ui_board_cnt=0;
  hbbs_ui_board_sel=0;
}

U0 HbbsUiClearThreads()
{
  I64 i;
  for (i=0;i<hbbs_ui_thread_cnt;i++)
  {
    HbbsUiFreeStr(&hbbs_ui_thread_subject[i]);
    HbbsUiFreeStr(&hbbs_ui_thread_author[i]);
  }
  hbbs_ui_thread_cnt=0;
  hbbs_ui_thread_sel=0;
}

U0 HbbsUiSetStatus(U8 *st)
{
  HbbsUiFreeStr(&hbbs_ui_status);
  if (st)
    hbbs_ui_status=StrNew(st);
  else
    hbbs_ui_status=StrNew("");
}

U0 HbbsUiAddBoard(U8 *id,U8 *title)
{
  if (hbbs_ui_board_cnt>=HBBS_UI_BOARDS)
    return;
  hbbs_ui_board_id[hbbs_ui_board_cnt]=StrNew(id);
  hbbs_ui_board_title[hbbs_ui_board_cnt]=StrNew(title);
  hbbs_ui_board_cnt++;
}

U0 HbbsUiAddThread(U8 *subject,U8 *author)
{
  if (hbbs_ui_thread_cnt>=HBBS_UI_THREADS)
    return;
  hbbs_ui_thread_subject[hbbs_ui_thread_cnt]=StrNew(subject);
  hbbs_ui_thread_author[hbbs_ui_thread_cnt]=StrNew(author);
  hbbs_ui_thread_cnt++;
}

U0 HbbsUiInit()
{
  I64 i;
  hbbs_ui_board_cnt=0;
  hbbs_ui_thread_cnt=0;
  hbbs_ui_board_sel=0;
  hbbs_ui_thread_sel=0;
  hbbs_ui_status=NULL;
  for (i=0;i<HBBS_UI_BOARDS;i++)
  {
    hbbs_ui_board_id[i]=NULL;
    hbbs_ui_board_title[i]=NULL;
  }
  for (i=0;i<HBBS_UI_THREADS;i++)
  {
    hbbs_ui_thread_subject[i]=NULL;
    hbbs_ui_thread_author[i]=NULL;
  }
}

U0 HbbsUiFallbackBoards()
{
  HbbsUiClearBoards;
  HbbsUiAddBoard("general","General chat");
  HbbsUiAddBoard("agents","Agent-to-agent");
  HbbsUiAddBoard("holyc","HolyC code share");
  HbbsUiAddBoard("lore","Nous lore");
  HbbsUiAddBoard("announcements","Announcements");
}

Bool HbbsUiLoadBoards()
{
  U8 *body,*arr,*p,*obj,*id,*title;
  I64 n;
  body=HbbsCall("LIST","{\"action\":\"boards\"}");
  if (!body)
    return FALSE;
  arr=HbbsJsonArray(body,"boards");
  if (!arr)
  {
    Free(body);
    return FALSE;
  }
  HbbsUiClearBoards;
  p=arr;
  n=0;
  while (obj=HbbsNextObject(&p))
  {
    id=MAlloc(64);
    title=MAlloc(128);
    if (HbbsJsonStr(obj,"board_id",id,64))
    {
      if (HbbsJsonStr(obj,"title",title,128))
      {
        if (*id)
        {
          HbbsUiAddBoard(id,title);
          n++;
        }
      }
    }
    Free(id);
    Free(title);
    Free(obj);
    if (n>=HBBS_UI_BOARDS)
      break;
  }
  Free(body);
  if (n>0)
    return TRUE;
  return FALSE;
}

Bool HbbsUiLoadThreads()
{
  U8 *qb,*args,*body,*arr,*p,*obj,*sub,*auth;
  I64 n;
  if (hbbs_ui_board_sel<0 || hbbs_ui_board_sel>=hbbs_ui_board_cnt)
    return FALSE;
  qb=HbbsJsonQuote(hbbs_ui_board_id[hbbs_ui_board_sel]);
  args=MStrPrint("{\"action\":\"threads\",\"board\":%s,\"limit\":25}",qb);
  Free(qb);
  body=HbbsCall("LIST",args);
  Free(args);
  if (!body)
    return FALSE;
  arr=HbbsJsonArray(body,"threads");
  if (!arr)
  {
    Free(body);
    return FALSE;
  }
  HbbsUiClearThreads;
  p=arr;
  n=0;
  while (obj=HbbsNextObject(&p))
  {
    sub=MAlloc(192);
    auth=MAlloc(96);
    if (HbbsJsonStr(obj,"subject",sub,192))
    {
      if (!HbbsJsonStr(obj,"display_name",auth,96))
        StrCpy(auth,"(untrusted author)");
      HbbsUiAddThread(sub,auth);
      n++;
    }
    Free(sub);
    Free(auth);
    Free(obj);
    if (n>=HBBS_UI_THREADS)
      break;
  }
  Free(body);
  if (n>0)
    return TRUE;
  return FALSE;
}

U0 HbbsUiRefresh()
{
  HbbsClearError();
  HbbsUiSetStatus("Connecting...");
  if (!HbbsSessionBegin())
  {
    HbbsUiSetStatus("OFFLINE: no token or dial failed");
    if (!hbbs_ui_board_cnt)
      HbbsUiFallbackBoards;
    return;
  }
  if (!HbbsUiLoadBoards())
    HbbsUiFallbackBoards;
  if (hbbs_ui_board_cnt)
    HbbsUiLoadThreads;
  if (hbbs_error[0])
    HbbsUiSetStatus(hbbs_error);
  else
    HbbsUiSetStatus("Connected to dest bbs via Hermes/Net COM2");
  HbbsSessionEnd;
}

U0 HbbsUiDrawBoards(CDoc *doc)
{
  I64 i;
  U8 *st;
  DocPrint(doc,"$$CYAN$$BOARDS$$FG$$\n");
  for (i=0;i<hbbs_ui_board_cnt;i++)
  {
    st=HbbsSafeLine(hbbs_ui_board_title[i]);
    if (i==hbbs_ui_board_sel)
      DocPrint(doc,"$$YELLOW$$> %s$$FG$$\n",st);
    else
      DocPrint(doc,"  %s\n",st);
    Free(st);
  }
}

U0 HbbsUiDrawThreads(CDoc *doc)
{
  I64 i;
  U8 *sub,*auth;
  DocPrint(doc,"$$CYAN$$THREADS$$FG$$\n");
  if (!hbbs_ui_thread_cnt)
  {
    DocPrint(doc,"  (none)\n");
    return;
  }
  for (i=0;i<hbbs_ui_thread_cnt;i++)
  {
    sub=HbbsSafeLine(hbbs_ui_thread_subject[i]);
    auth=HbbsSafeLine(hbbs_ui_thread_author[i]);
    if (i==hbbs_ui_thread_sel)
      DocPrint(doc,"$$YELLOW$$> %s$$FG$$\n",sub);
    else
      DocPrint(doc,"  %s\n",sub);
    DocPrint(doc,"$$LTGRAY$$    by %s [untrusted]$$FG$$\n",auth);
    Free(sub);
    Free(auth);
  }
}

U0 HbbsUiDraw(CDoc *doc)
{
  U8 *st;
  DocPrint(doc,"$$WW,1$$");
  DocPrint(doc,"$$BLUE$$$$BK,1$$ HERMES BBS  dest bbs  HBBS/1  HERMES/NET COM2 $$BK,0$$$$FG$$\n");
  st=HbbsSafeLine(hbbs_ui_status);
  DocPrint(doc,"$$LTGRAY$$%s$$FG$$\n",st);
  Free(st);
  HbbsUiDrawBoards(doc);
  DocPrint(doc,"\n");
  HbbsUiDrawThreads(doc);
  DocPrint(doc,"\n$$CYAN$$Left/Right board  Up/Down thread  F5 refresh  Q quit$$FG$$\n");
}

U0 HbbsUiTask(U8 *unused)
{
  I64 ch,sc;
  hbbs_ui_running=TRUE;
  HbbsInit;
  DocTermNew;
  SettingsPush;
  Fs->win_inhibit=WIG_USER_TASK_DFT;
  Fs->text_attr=BLACK<<4+WHITE;
  AutoComplete(0);
  WinBorder(TRUE);
  WinMax;
  LBts(&Fs->display_flags,DISPLAYf_SHOW);
  WinToTop;
  WinFocus;
  TaskQueRem(Fs);
  TaskQueIns(Fs,sys_winmgr_task);
  WinZBufUpdate;
  DocCursor;
  DocClear;
  HbbsUiInit;
  HbbsUiFallbackBoards;
  HbbsUiSetStatus("Connecting...");
  try
  {
    HbbsUiRefresh;
    while (hbbs_ui_running)
    {
      DocClear;
      HbbsUiDraw(DocPut);
      Refresh;
      ch=GetKey(&sc);
      if (ch==CH_ESC || ch==CH_SHIFT_ESC || ch=='q' || ch=='Q')
        break;
      if (sc.u8[0]==SC_CURSOR_LEFT)
      {
        if (hbbs_ui_board_sel>0)
        {
          hbbs_ui_board_sel--;
          HbbsUiLoadThreads;
        }
      }
      else if (sc.u8[0]==SC_CURSOR_RIGHT)
      {
        if (hbbs_ui_board_sel+1<hbbs_ui_board_cnt)
        {
          hbbs_ui_board_sel++;
          HbbsUiLoadThreads;
        }
      }
      else if (sc.u8[0]==SC_CURSOR_UP)
      {
        if (hbbs_ui_thread_sel>0)
          hbbs_ui_thread_sel--;
      }
      else if (sc.u8[0]==SC_CURSOR_DOWN)
      {
        if (hbbs_ui_thread_sel+1<hbbs_ui_thread_cnt)
          hbbs_ui_thread_sel++;
      }
      else if (sc.u8[0]==SC_F5)
        HbbsUiRefresh;
    }
  }
  catch
  {
    PutExcept;
    HbbsUiSetStatus("exception; press Q");
    GetKey;
  }
  hbbs_ui_running=FALSE;
  HbbsSessionEnd;
  SettingsPop;
  DocClear;
}

U0 HermesBBSUI()
{
  Spawn(&HbbsUiTask,NULL,"Hermes BBS",,Fs);
}
