// THE TEMPLE OF HERMES — shared globals and constants.
// Public-domain work, with credit to Terry A. Davis (TempleOS)
// and the TinkerOS authors (tinkeros/TinkerOS).

#define HERMES_VERSION		"0.1.0"
#define HERMES_NAME		"TempleOfHermes"
#define HERMES_COM		1
#define HERMES_BAUD		115200
#define HERMES_MAX_PAYLOAD	262144
#define HERMES_MAX_EVT		32
#define HERMES_MAX_TASKS	80

#define HERMES_MODE_USER	0
#define HERMES_MODE_SHARED	1
#define HERMES_MODE_AGENT	2

public I64 hermes_mode=HERMES_MODE_USER;
public I64 hermes_agent_mx=320;
public I64 hermes_agent_my=240;
public I64 hermes_started=FALSE;
public I64 hermes_evt_seq=0;
public I64 hermes_ready=FALSE;
public CTask *hermes_task=NULL;

public U0 (*hermes_old_wall)(CTask *task)=NULL;
public U0 (*hermes_old_ms)(CDC *dc,I64 x,I64 y)=NULL;
public U0 (*hermes_old_final)(CDC *dc)=NULL;

class CHermesEvt
{
  I64 seq;
  F64 t;
  U8  kind[32];
  U8  data[192];
};

public CHermesEvt hermes_evts[HERMES_MAX_EVT];
public I64 hermes_evt_head=0;
public I64 hermes_evt_tail=0;

public I64 hermes_seen_tasks[HERMES_MAX_TASKS];
public I64 hermes_seen_cnt=0;
public U8  hermes_last_prompt[256];
public I64 hermes_prompt_armed=FALSE;
public U8  hermes_toast[192];
public F64 hermes_toast_until=0.0;

U8 *HermesModeName()
{
  switch (hermes_mode)
  {
  case HERMES_MODE_AGENT:
    return "agent";
  case HERMES_MODE_SHARED:
    return "shared";
  default:
    return "user";
  }
}

I64 HermesModeFromName(U8 *s)
{
  if (!s) return HERMES_MODE_USER;
  if (!StrICmp(s,"agent"))  return HERMES_MODE_AGENT;
  if (!StrICmp(s,"shared")) return HERMES_MODE_SHARED;
  if (!StrICmp(s,"user"))   return HERMES_MODE_USER;
  return -1;
}

U8 *HermesEsc(U8 *s)
{
  I64 i,j,len;
  U8 *d;
  if (!s) s="";
  len=StrLen(s);
  d=MAlloc(len*2+1);
  j=0;
  for (i=0; i<len; i++)
  {
    if (s[i]=='"' || s[i]=='\\')
    {
      d[j++]='\\';
      d[j++]=s[i];
    }
    else if (s[i]=='\n')
    {
      d[j++]='\\';
      d[j++]='n';
    }
    else if (s[i]=='\r')
    {
      d[j++]='\\';
      d[j++]='r';
    }
    else if (s[i]=='\t')
    {
      d[j++]='\\';
      d[j++]='t';
    }
    else if (s[i]>=32 && s[i]<127)
      d[j++]=s[i];
  }
  d[j]=0;
  return d;
}
