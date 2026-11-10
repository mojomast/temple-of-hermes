#define HBBS_DEST "bbs"
#define HBBS_PROTO "HBBS/1"
#define HBBS_BODY_MAX 16384
#define HBBS_LINE_MAX 512
#define HBBS_TOKEN_MAX 1024
#define HBBS_RX_MAX 4096
#define HBBS_PATH_MAX 256
#define HBBS_RESULT_DIR "::/Hermes/Apps/HermesBBS/Results"
#define HBBS_TOKEN_REL "Apps/HermesBBS/token"
#define HBBS_TOKEN_ALT "BBS/token"

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
I64 hbbs_last_ok;

U0 HbbsSetError(U8 *st)
{
  if (!st) st="error";
  StrCpy(hbbs_error,st);
  hbbs_error[sizeof(hbbs_error)-1]=0;
}

U0 HbbsClearError()
{
  hbbs_error[0]=0;
}

U8 *HbbsFindRel(U8 *rel)
{
  I64 i;
  U8 *st;
  for (i=0;i<4;i++)
  {
    st=MStrPrint("%s%s",hbbs_roots[i],rel);
    if (IsFile(st))
      return st;
    Free(st);
  }
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
  U8 *st,*data,*p,*d;
  I64 size,n;
  hbbs_token[0]=0;
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
  U8 *st;
  I64 n;
  if (!tok || !*tok)
    return FALSE;
  DirMk("::/Hermes/Apps/HermesBBS");
  st=MStrPrint("::/Hermes/%s",HBBS_TOKEN_REL);
  n=StrLen(tok);
  FileWrite(st,tok,n);
  Free(st);
  return TRUE;
}

Bool HbbsLoadClaim()
{
  U8 *st,*data,*p,*d;
  I64 size,n;
  hbbs_claim[0]=0;
  st=MStrPrint("::/Hermes/Apps/HermesBBS/claim");
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
  U8 *st;
  I64 n;
  if (!tok || !*tok)
    return FALSE;
  DirMk("::/Hermes/Apps/HermesBBS");
  st=MStrPrint("::/Hermes/Apps/HermesBBS/claim");
  n=StrLen(tok);
  FileWrite(st,tok,n);
  Free(st);
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
  *d++='"';
  while (c=*src++)
  {
    if (c=='"')
    {
      *d++='\\';
      *d++='"';
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
  *d++='"';
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
  if (!p || *p!='"')
    return FALSE;
  p++;
  while (*p && *p!='"')
  {
    if (*p=='\\')
    {
      p++;
      if (!*p)
        break;
      switch (*p)
      {
      case '"': v='"'; break;
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
      else if (c=='"')
        instr=FALSE;
    }
    else
    {
      if (c=='"')
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
    if (c=='$' || c=='`')
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
  U8 *keys[5]={"access_token","refresh_token","claim_token","password","token"};
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
          if (*q=='"')
          {
            r=q+1;
            while (*r)
            {
              if (*r=='\\' && r[1])
                r+=2;
              else if (*r=='"')
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
    n=HermesNetRecv(hbbs_rxbuf,sizeof(hbbs_rxbuf),200);
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
  if (!HbbsReadLine(line,sizeof(line),30000))
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
  while (*p && *p!=' ' && q<id+sizeof(id)-1)
    *q++=*p++;
  *q=0;
  while (*p==' ')
    p++;
  q=rcmd;
  while (*p && *p!=' ' && q<rcmd+sizeof(rcmd)-1)
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
  DirMk("::/Hermes/Apps/HermesBBS");
  DirMk(HBBS_RESULT_DIR);
  hbbs_seq++;
  StrPrint(hbbs_result_path,"%s/%03d-%s.json",HBBS_RESULT_DIR,hbbs_seq,op);
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
  last=MStrPrint("%s/last.json",HBBS_RESULT_DIR);
  n=StrLen(op)+StrLen(cmd)+StrLen(err?err:"")+StrLen(data_json)+512;
  path=MAlloc(n);
  StrPrint(path,
    "{\"v\":1,\"hbbs\":\"%s\",\"dest\":\"%s\",\"transport\":\"hermes-net/com2\","
    "\"op\":\"%s\",\"command\":\"%s\",\"request_id\":\"%s\","
    "\"ok\":%d,\"error\":\"%s\",\"trust\":\"untrusted\",\"data\":%s}\n",
    HBBS_PROTO,HBBS_DEST,op,cmd,hbbs_last_id,ok,err?err:"",data_json);
  FileWrite(hbbs_result_path,path,StrLen(path));
  FileWrite(last,path,StrLen(path));
  Free(path);
  Free(last);
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
