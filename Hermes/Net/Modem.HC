// Guest-side Hayes modem client for THE TEMPLE OF HERMES.
//
// The host runs host/hermes_modem.py on the other end of COM2.  Networking is
// off there by default; Dial() succeeds only for destinations on the host
// allow-list (for example "hermes").  See docs/NETWORKING.md.

// Bring up COM2 without disturbing COM1.
//
// CommInit() is a *global* reset: it clears every comm_ports[] slot, including
// the COM1 state owned by the Hermes daemon.  Calling it from an app that
// merely wants the modem made the daemon's next HEVT write throw ComErr and
// stop the whole guest (the dead black "Hermes App" window).  Only call the
// global initializer when no port has been brought up yet; otherwise fill in
// just the COM2 base and configure that UART.
Bool HermesNetInit()
{
  CComm *c=&comm_ports[HERMES_NET_COM];
  if (!comm_ports[1].base && !comm_ports[HERMES_NET_COM].base)
    CommInit;
  if (!c->base)
    c->base=0x2F8;
  CommInit8n1(HERMES_NET_COM,HERMES_NET_BAUD);
  CommFlush(HERMES_NET_COM);
  return TRUE;
}

// Dial an allow-listed destination.  Returns TRUE only after CONNECT.
Bool HermesNetDial(U8 *dest)
{
  U8 line[HERMES_NET_LINE_MAX];
  F64 timeout_time;
  if (!dest || !*dest)
    return FALSE;
  try
  {
    HermesNetInit;
  }
  catch
  {
    Fs->catch_except=TRUE;
    return FALSE;
  }
  HermesNetResetState;
  HermesNetPutS("ATZ\r");
  if (!HermesNetReadLine(line,sizeof(line),1500))
    return FALSE;
  if (StrCmp(line,"OK"))
    return FALSE;
  StrPrint(line,"ATD %s\r",dest);
  HermesNetPutS(line);
  timeout_time=tS+5.0;
  while (tS<timeout_time)
  {
    if (HermesNetReadLine(line,sizeof(line),1000))
    {
      if (!StrNCmp(line,"CONNECT",7))
      {
        StrCpy(hermes_net_dest,dest);
        hermes_net_open=TRUE;
        return TRUE;
      }
      if (!StrCmp(line,"ERROR") || !StrCmp(line,"NO CARRIER") ||
          !StrCmp(line,"BUSY"))
        return FALSE;
    }
  }
  return FALSE;
}

// Send len bytes.  Returns len, or -1 if the modem is not connected.
I64 HermesNetSend(U8 *buf,I64 len)
{
  U8 line[64];
  if (!hermes_net_open || !buf || len<=0)
    return -1;
  StrPrint(line,"AT+SEND %d\r",len);
  HermesNetPutS(line);
  HermesNetPutBlk(buf,len);
  if (!HermesNetReadLine(line,sizeof(line),5000))
    return -1;
  if (StrNCmp(line,"OK",2))
    return -1;
  return len;
}

// Ask for up to max bytes.  Returns bytes read, 0 for an empty frame, or -1
// when the modem is not connected.
I64 HermesNetRecv(U8 *buf,I64 max,I64 timeout_ms=1000)
{
  U8 line[64];
  I64 n;
  if (!hermes_net_open || !buf || max<=0)
    return -1;
  StrPrint(line,"AT+RECV %d\r",max);
  HermesNetPutS(line);
  if (!HermesNetReadLine(line,sizeof(line),timeout_ms))
    return -1;
  if (StrNCmp(line,"DATA ",5))
    return -1;
  n=Str2I64(line+5);
  if (n<0) n=0;
  if (n>max) n=max;
  return HermesNetReadBlk(buf,n,timeout_ms);
}

// Hang up.  Safe to call when already idle.
Bool HermesNetHangUp()
{
  U8 line[HERMES_NET_LINE_MAX];
  Bool ok;
  if (!comm_ports[HERMES_NET_COM].base)
  {
    HermesNetResetState;
    return FALSE;
  }
  HermesNetPutS("ATH\r");
  ok=HermesNetReadLine(line,sizeof(line),2000);
  HermesNetResetState;
  if (!ok)
    return FALSE;
  return !StrCmp(line,"OK");
}

// Human-readable one-line status for the command line.
U0 HermesNetStatus()
{
  if (hermes_net_open)
    "HERMES/NET COM%d connected to %s\n",HERMES_NET_COM,hermes_net_dest;
  else
    "HERMES/NET COM%d idle (host modem off by default)\n",HERMES_NET_COM;
}
