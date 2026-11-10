// Low-level COM2 byte and line helpers for the Hermes modem client.

U0 HermesNetPutChar(U8 ch)
{
  CommPutChar(HERMES_NET_COM,ch);
}

U0 HermesNetPutS(U8 *st)
{
  if (st)
    CommPutS(HERMES_NET_COM,st);
}

U0 HermesNetPutBlk(U8 *buf,I64 len)
{
  if (buf && len>0)
    CommPutBlk(HERMES_NET_COM,buf,len);
}

Bool HermesNetGetCharNoWait(U8 *ch)
{
  if (!ch) return FALSE;
  return CommGetCharNoWait(HERMES_NET_COM,ch);
}

// Read one CR/LF-terminated line.  Returns FALSE on timeout.
Bool HermesNetReadLine(U8 *buf,I64 max,I64 timeout_ms=1000)
{
  U8 ch;
  I64 n=0;
  F64 timeout_time;
  if (!buf || max<=0) return FALSE;
  timeout_time=tS+ToF64(timeout_ms)/1000.0;
  while (tS<=timeout_time)
  {
    if (HermesNetGetCharNoWait(&ch))
    {
      if (ch=='\n')
      {
        if (n>0 && buf[n-1]=='\r') n--;
        buf[n]=0;
        StrCpy(hermes_net_last,buf);
        return TRUE;
      }
      if (n<max-1) buf[n++]=ch;
    }
    else
      Yield;
  }
  buf[n]=0;
  return FALSE;
}

// Read exactly count bytes, with an overall timeout.  Returns bytes read.
I64 HermesNetReadBlk(U8 *buf,I64 count,I64 timeout_ms=1000)
{
  U8 ch;
  I64 n=0;
  F64 timeout_time;
  if (!buf || count<=0) return 0;
  timeout_time=tS+ToF64(timeout_ms)/1000.0;
  while (n<count)
  {
    if (HermesNetGetCharNoWait(&ch))
      buf[n++]=ch;
    else
    {
      if (tS>timeout_time) break;
      Yield;
    }
  }
  return n;
}
