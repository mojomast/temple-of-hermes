#define TR_W 640
#define TR_H 480
#define TR_MAX 28
#define TR_PY 400
#define TR_L 40
#define TR_R 600
#define TR_TOP 56

class CToken
{
  F64 x,y,vy;
  I64 kind;
  Bool on;
};

CToken tr_tok[TR_MAX];
I64 tr_state,tr_score,tr_high,tr_lives,tr_catches,tr_hits,tr_frames;
F64 tr_px,tr_spawn,tr_flash;
U32 tr_seed,tr_seed0;
Bool tr_agent,tr_kl,tr_kr;
CDC *tr_hdr,*tr_gr,*tr_plate,*tr_icon32,*tr_icon16;

F64 TRRandF()
{
  tr_seed=tr_seed*1103515245+12345;
  return ((tr_seed>>8)&0xFFFFFF)/16777216.0;
}

I64 TRRand(I64 n)
{
  tr_seed=tr_seed*1103515245+12345;
  if (n<1)
    n=1;
  return (tr_seed>>8)%n;
}

U0 TRSaveHigh()
{
  U8 *s;
  if (!IsDir("C:/Tmp"))
    DirMk("C:/Tmp");
  s=MStrPrint("%d\n",tr_high);
  FileWrite("C:/Tmp/TokenRainScore.TXT",s,StrLen(s));
  Free(s);
}

U0 TRLoadHigh()
{
  U8 *s=FileRead("C:/Tmp/TokenRainScore.TXT");
  tr_high=0;
  if (s)
  {
    tr_high=Str2I64(s);
    Free(s);
  }
  TRSaveHigh;
}

U0 TRReset(Bool agent)
{
  I64 i;
  U32 seed;
  tr_state=1;
  tr_score=0;
  tr_lives=3;
  tr_catches=0;
  tr_hits=0;
  tr_frames=0;
  tr_px=320.0;
  tr_spawn=0.5;
  tr_flash=0;
  tr_agent=agent;
  tr_kl=tr_kr=FALSE;
  if (agent)
    tr_seed=0x5EED1234;
  else
  {
    seed=tS*1000.0;
    tr_seed=seed+0x9E3779B9;
  }
  tr_seed0=tr_seed;
  for (i=0;i<TR_MAX;i++)
    tr_tok[i].on=FALSE;
}
