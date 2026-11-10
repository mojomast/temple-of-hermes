#ifndef HERMES_NET_APP_NET_HC
#define HERMES_NET_APP_NET_HC

#help_index "Hermes/Apps"

//THE TEMPLE OF HERMES - Modem / Net status and loopback tools.
//
//This is a small command-line app over the real Hermes/Net library.  COM2 is
//the modem link; COM1 remains the Hermes HRPC console.  Nothing dials until a
//tool is called, and the only destination used here is the allow-listed name
//"hermes" (never a hostname or an address).

#define HERMES_NET_APP_TITLE	"THE TEMPLE OF HERMES - Modem / Net"
#define HERMES_NET_ECHO_MAX	128
#define HERMES_NET_ECHO_WAIT	3000

public Bool hermes_net_icon_loaded=FALSE;
public U8 hermes_net_echo_tx[HERMES_NET_ECHO_MAX+1];
public U8 hermes_net_echo_rx[HERMES_NET_ECHO_MAX+1];
public I64 hermes_net_echo_tx_len=0;
public I64 hermes_net_echo_rx_len=0;
public I64 hermes_net_echo_result=0;
U8 *hermes_net_roots[5]={"::/Hermes/","B:/Hermes/","C:/Hermes/","T:/Hermes/","~/Hermes/"};

U8 *HermesNetFind(U8 *rel)
{//Find rel under a Hermes tree.  Returns an allocated path or NULL.
  I64 i;
  U8 *st;
  for (i=0;i<5;i++)
  {
    st=MStrPrint("%s%s",hermes_net_roots[i],rel);
    if (IsFile(st))
      return st;
    Free(st);
  }
  return NULL;
}

U8 *HermesNetIconPath()
{
  return HermesNetFind("Art/Icons/32/modem-net.GR");
}

Bool HermesNetLoadIcon()
{//Load the official modem-net icon from Hermes/Art; never generate one.
  U8 *st;
  CDC *dc;
  hermes_net_icon_loaded=FALSE;
  st=HermesNetIconPath();
  if (!st)
    return FALSE;
  dc=GRRead(st);
  Free(st);
  if (!dc)
    return FALSE;
  hermes_net_icon_loaded=dc->width>0 && dc->height>0;
  DCDel(dc);
  return hermes_net_icon_loaded;
}

U0 HermesNetPrintStatus()
{//Port, baud, state and destination; safe to call repeatedly.
  "HERMES/NET modem status\n";
  "  port: COM%d (0x2F8, IRQ 3)\n",HERMES_NET_COM;
  "  baud: %d 8N1\n",HERMES_NET_BAUD;
  "  state: %s\n",HermesNetStateName;
  if (hermes_net_open)
    "  destination: %s\n",hermes_net_dest;
  else
    "  destination: (none; host modem is off by default)\n";
  if (HermesNetLoadIcon())
    "  art: modem-net 32x32 loaded\n";
  else
    "  art: modem-net icon not found; text fallback\n";
  "  COM1 HRPC is not touched by this app.\n";
}

U0 HermesNetUsage()
{
  "tools: HermesNetStatus;  HermesNetEchoTest;  HermesNetHangUp;\n";
  "HermesNetEchoTest dials the allow-listed name \"hermes\", sends one\n";
  "small frame, and checks the host echo.  It never dials a hostname.\n";
}

U0 HermesNetApp()
{//Entry point for Run.HC.  Prints status and returns to the shell.
  if (!comm_ports[HERMES_NET_COM].base)
  {
    try
    {
      HermesNetInit;
    }
    catch
    {
      Fs->catch_except=TRUE;
    }
  }
  HERMES_NET_APP_TITLE;
  "\n";
  HermesNetPrintStatus;
  "\n";
  HermesNetUsage;
  "Run.HC returns to the shell; the link stays idle until a tool dials.\n";
}

I64 HermesNetEchoTest()
{//Dial "hermes", send one frame, and compare the host echo.
  U8 tx[HERMES_NET_ECHO_MAX+1];
  U8 rx[HERMES_NET_ECHO_MAX+1];
  I64 n,m,len;
  Bool ok;
  MemSet(tx,0,sizeof(tx));
  MemSet(rx,0,sizeof(rx));
  hermes_net_echo_tx_len=0;
  hermes_net_echo_rx_len=0;
  hermes_net_echo_result=0;
  StrPrint(tx,"HERMES-NET-ECHO-01");
  len=StrLen(tx);
  "modem-net loopback: dialing \"hermes\"...\n";
  if (!HermesNetDial("hermes"))
  {
    "modem-net loopback: dial failed (host modem off or allow-list denied)\n";
    return -1;
  }
  "modem-net loopback: connected\n";
  n=HermesNetSend(tx,len);
  if (n!=len)
  {
    "modem-net loopback: send failed (n=%d)\n",n;
    HermesNetHangUp;
    return -1;
  }
  hermes_net_echo_tx_len=n;
  StrCpy(hermes_net_echo_tx,tx);
  "guest->stub %d bytes: %s\n",n,tx;
  m=HermesNetRecv(rx,HERMES_NET_ECHO_MAX,HERMES_NET_ECHO_WAIT);
  if (m<0)
  {
    "modem-net loopback: receive failed\n";
    HermesNetHangUp;
    return -1;
  }
  rx[m]=0;
  hermes_net_echo_rx_len=m;
  StrCpy(hermes_net_echo_rx,rx);
  "stub->guest %d bytes: %s\n",m,rx;
  ok=m==len && !StrCmp(rx,tx);
  if (ok)
    "modem-net loopback: ECHO OK\n";
  else
    "modem-net loopback: ECHO MISMATCH\n";
  HermesNetHangUp;
  if (ok)
    hermes_net_echo_result=0;
  else
    hermes_net_echo_result=1;
  return hermes_net_echo_result;
}

#help_index ""

#endif
