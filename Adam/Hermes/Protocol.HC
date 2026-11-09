// Length-prefixed text frames on COM1.
//   HBEACON TempleOfHermes/0.1.0\n
//   HREQ <id> <op> <len>\n  + <len bytes>
//   HRPL <id> <ok|err> <len>\n + <len bytes>
//   HEVT <seq> <kind> <len>\n + <len bytes>

U0 HermesPutChar(U8 b)
{
  CommPutChar(HERMES_COM,b);
}

U0 HermesPutS(U8 *s)
{
  CommPutS(HERMES_COM,s);
}

U0 HermesPutBlk(U8 *buf,I64 len)
{
  if (buf && len>0)
    CommPutBlk(HERMES_COM,buf,len);
}

U0 HermesSendRaw(U8 *kind,I64 id,U8 *stat,U8 *payload,I64 len)
{
  U8 hdr[160];
  if (len<0) len=0;
  if (!payload) len=0;
  StrPrint(hdr,"%s %d %s %d\n",kind,id,stat,len);
  HermesPutS(hdr);
  HermesPutBlk(payload,len);
}

U0 HermesReply(I64 id,U8 *payload)
{
  I64 len=0;
  if (payload) len=StrLen(payload);
  HermesSendRaw("HRPL",id,"ok",payload,len);
}

U0 HermesReplyErr(I64 id,U8 *msg)
{
  I64 len=0;
  if (msg) len=StrLen(msg);
  HermesSendRaw("HRPL",id,"err",msg,len);
}

U0 HermesReplyLen(I64 id,U8 *payload,I64 len)
{
  HermesSendRaw("HRPL",id,"ok",payload,len);
}

U0 HermesBeacon()
{
  U8 line[128];
  StrPrint(line,"HBEACON %s/%s\n",HERMES_NAME,HERMES_VERSION);
  HermesPutS(line);
}

Bool HermesGetCharNoWait(U8 *ch)
{
  return CommGetCharNoWait(HERMES_COM,ch);
}

U8 HermesGetChar()
{
  return CommGetChar(HERMES_COM);
}
