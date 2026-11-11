#ifndef HERMES_CHAT_LOAD_HC
#define HERMES_CHAT_LOAD_HC

// THE TEMPLE OF HERMES - Hermes Chat.
//
// Hermes Chat is a tiny HolyC client for the COM2 Hayes modem.  It compiles
// the real Hermes/Net library (Load.HC -> Glbls/Protocol/Modem) from the
// sibling Net directory; no inline copy of the modem code lives here.
//
// Wire format inside an AT+SEND / AT+RECV frame:
//   guest -> host:  "HCHAT1 <text>"
//   host -> guest:  "HCHAT1 <text>" or "HCHAT1-ERR <reason>"
//
// The destination is the allow-listed name "hermes".  See
// docs/HERMES-CHAT-PROTOCOL.md.

#help_index "Hermes/Apps"
Cd(__DIR__);;
#include "../../Net/Load.HC"
Cd(__DIR__);;

#define HERMES_CHAT_MAX                 768
#define HERMES_CHAT_PREFIX              "HCHAT1 "
#define HERMES_CHAT_ERR_PREFIX          "HCHAT1-ERR "
#define HERMES_CHAT_REPLY_TIMEOUT_MS    5000

public Bool hermes_chat_icon_loaded=FALSE;
U8 *hermes_chat_roots[5]={"::/Hermes/","B:/Hermes/","C:/Hermes/","T:/Hermes/","~/Hermes/"};

U0 HermesChatCopy(U8 *dst,I64 max,U8 *src)
{//Bounded copy that always terminates dst.
  I64 n;
  if (!dst || max<=0)
    return;
  if (!src)
  {
    dst[0]=0;
    return;
  }
  n=StrLen(src);
  if (n>=max)
    n=max-1;
  MemCpy(dst,src,n);
  dst[n]=0;
}

U8 *HermesChatFind(U8 *rel)
{//Find rel under a Hermes tree.  Returns an allocated path or NULL.
  I64 i;
  U8 *st;
  for (i=0;i<5;i++)
  {
    st=MStrPrint("%s%s",hermes_chat_roots[i],rel);
    if (IsFile(st))
      return st;
    Free(st);
  }
  return NULL;
}

U8 *HermesChatIconPath()
{
  return HermesChatFind("Art/Icons/32/hermes-chat.GR");
}

Bool HermesChatLoadIcon()
{//Use the checked-in hermes-chat art when the overlay shipped it.
  U8 *st;
  CDC *dc;
  hermes_chat_icon_loaded=FALSE;
  st=HermesChatIconPath();
  if (!st)
    return FALSE;
  dc=GRRead(st);
  Free(st);
  if (!dc)
    return FALSE;
  hermes_chat_icon_loaded=dc->width>0 && dc->height>0;
  DCDel(dc);
  return hermes_chat_icon_loaded;
}

Bool HermesChatConnect()
{//Dial the allow-listed Hermes destination through the compiled Net lib.
  if (hermes_net_open)
    return TRUE;
  return HermesNetDial("hermes");
}

I64 HermesChatSendText(U8 *text)
{//Send one HCHAT1 frame.  Returns the byte count or -1.
  U8 frame[HERMES_CHAT_MAX+1];
  I64 n;
  if (text)
    StrPrint(frame,"HCHAT1 %s",text);
  else
    StrPrint(frame,"HCHAT1 ");
  n=StrLen(frame);
  if (n>HERMES_CHAT_MAX)
    n=HERMES_CHAT_MAX;
  return HermesNetSend(frame,n);
}

I64 HermesChatRecvText(U8 *out,I64 max,I64 timeout_ms=HERMES_CHAT_REPLY_TIMEOUT_MS)
{//Receive one response frame.  Returns text length, 0, or -1.
  U8 buf[HERMES_CHAT_MAX+1];
  I64 n;
  if (!out || max<=0)
    return -1;
  out[0]=0;
  n=HermesNetRecv(buf,HERMES_CHAT_MAX,timeout_ms);
  if (n<=0)
    return n;
  buf[n]=0;
  while (n>0 && (buf[n-1]=='\r' || buf[n-1]=='\n'))
    buf[--n]=0;
  if (!StrNCmp(buf,HERMES_CHAT_ERR_PREFIX,StrLen(HERMES_CHAT_ERR_PREFIX)))
  {
    HermesChatCopy(out,max,buf+StrLen(HERMES_CHAT_ERR_PREFIX));
    return -1;
  }
  if (!StrNCmp(buf,HERMES_CHAT_PREFIX,StrLen(HERMES_CHAT_PREFIX)))
  {
    HermesChatCopy(out,max,buf+StrLen(HERMES_CHAT_PREFIX));
    return StrLen(out);
  }
  HermesChatCopy(out,max,buf);
  return StrLen(out);
}

U0 HermesChatBuildCheck()
{//Compile/load evidence helper; called explicitly from the guest shell.
  "HERMES/CHAT BUILD OK\n";
  "destination=hermes  net=%s\n",HermesNetStateName;
  if (HermesChatLoadIcon())
    "art=hermes-chat 32x32 loaded\n";
  else
    "art=hermes-chat not found (using text fallback)\n";
  if (comm_ports[1].base)
    CommPutS(1,"HERMES_CHAT_BUILD_OK\n");
}

U0 HermesChatTask(U8 *)
{
  U8 reply[HERMES_CHAT_MAX+1];
  U8 *line;
  I64 n;
  Bool connected;

  DocTermNew;
  SettingsPush;
  AutoComplete(FALSE);
  StrCpy(Fs->task_title,"Hermes Chat");
  Fs->title_src=TTS_LOCKED_CONST;
  Fs->win_inhibit=WIG_USER_TASK_DFT;
  WinBorder(TRUE);
  LBts(&Fs->display_flags,DISPLAYf_SHOW);
  WinToTop;
  WinFocus;
  DocPrint(, "THE TEMPLE OF HERMES - Hermes Chat\n");
  DocPrint(, "COM%d modem, destination \"hermes\"\n",HERMES_NET_COM);
  if (HermesChatLoadIcon())
    DocPrint(, "art: hermes-chat 32x32 loaded\n");
  else
    DocPrint(, "art: text fallback\n");

  connected=HermesChatConnect();
  if (connected)
    DocPrint(, "connected: CONNECT hermes\n\n");
  else
  {
    DocPrint(, "dial failed: host modem off or allow-list denied\n");
    DocPrint(, "type /connect to retry, /quit to hang up\n\n");
  }
  Refresh;

  while (TRUE)
  {
    line=GetStr("you> ",,GSF_SHIFT_ESC_EXIT);
    if (!line)
      break;
    if (!*line)
      Free(line);
    else if (!StrCmp(line,"/quit"))
    {
      Free(line);
      break;
    }
    else if (!StrCmp(line,"/connect"))
    {
      Free(line);
      if (HermesChatConnect())
        DocPrint(, "connected: CONNECT hermes\n");
      else
        DocPrint(, "connect failed\n");
    }
    else if (!connected)
    {
      Free(line);
      DocPrint(, "not connected; type /connect first\n");
    }
    else
    {
      n=HermesChatSendText(line);
      Free(line);
      if (n<0)
      {
        DocPrint(, "send failed\n");
        connected=FALSE;
      }
      else
      {
        n=HermesChatRecvText(reply,sizeof(reply),HERMES_CHAT_REPLY_TIMEOUT_MS);
        if (n>0)
          DocPrint(, "hermes> %s\n",reply);
        else if (n==0)
        {
          DocPrint(, "hermes> (no reply)\n");
          connected=FALSE;
        }
        else
        {
          DocPrint(, "hermes> %s\n",reply);
          connected=FALSE;
        }
      }
    }
    Refresh;
  }
  if (hermes_net_open)
    HermesNetHangUp;
  SettingsPop;
  Refresh;
}

U0 HermesChatRun()
{//Run Hermes Chat in the calling task so the launcher can restore after Esc.
  HermesChatTask(NULL);
}

#help_index ""

#endif
