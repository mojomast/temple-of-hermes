#ifndef DUEL_STATE_V2_HC_V5
#define DUEL_STATE_V2_HC_V5
#include "DuelText.HC"
U0 DuelSaveBest()
{
  U8 *s,*path;
  s=MStrPrint("DOJO DUEL HIGH SCORE\nBEST: %d\nSTREAK: %d\nRUNS: %d\n",
    duel_best,duel_beststreak,duel_runs);
  path=DuelScorePath();
  if (path && *path)
  {
    try
    {
      FileWrite(path,s,StrLen(s));
    }
    catch
      Fs->catch_except=TRUE;
  }
  Free(path);
  Free(s);
}
U0 DuelLoadBest()
{
  U8 *path,*b,*p;
  duel_best=0; duel_beststreak=0; duel_runs=0;
  path=DuelScorePath();
  b=NULL;
  if (path && *path && FileFind(path))
    b=FileRead(path);
  Free(path);
  if (b)
  {
    p=StrFind("BEST: ",b);    if (p) duel_best=Str2I64(p+6);
    p=StrFind("STREAK: ",b);  if (p) duel_beststreak=Str2I64(p+8);
    p=StrFind("RUNS: ",b);    if (p) duel_runs=Str2I64(p+6);
    Free(b);
  }
}
U0 DuelFinish()
{
  duel_state=DUEL_DONE;
  duel_runs++;
  if (duel_score>duel_best) duel_best=duel_score;
  if (duel_best_streak>duel_beststreak) duel_beststreak=duel_best_streak;
  DuelSaveBest;
  DuelFlash("DUEL COMPLETE - NEW");
}
U0 DuelNext()
{
  if (duel_idx>=DUEL_NCH) { DuelFinish; return; }
  duel_buf[0]=0;
  duel_startt=tS;
  duel_deadline=tS+DUEL_TIME;
  duel_lastok=-1; duel_lasttime=0;
}
U0 DuelSubmit(Bool timed_out)
{
  I64 ok=FALSE,remain,gain;
  if (duel_state!=DUEL_PLAY) return;
  if (!timed_out && DuelEq(duel_buf,duel_tokens[duel_idx])) ok=TRUE;
  duel_pass[duel_idx]=ok;
  duel_lasttime=timed_out;
  if (ok)
  {
    remain=ToI64(duel_deadline-tS);
    if (remain<0) remain=0;
    gain=100+remain*10+duel_streak*20;
    duel_score+=gain;
    duel_streak++;
    if (duel_streak>duel_best_streak) duel_best_streak=duel_streak;
    duel_lastok=1; duel_lastgain=gain;
    DuelFlash("CLEAN STRIKE - NEW");
  }
  else
  {
    duel_streak=0; duel_lastok=0; duel_lastgain=0;
    if (timed_out) DuelFlash("TIME - NEW");
    else DuelFlash("MISS - NEW");
  }
  duel_idx++;
  if (duel_idx>=DUEL_NCH) { DuelFinish; }
  else { DuelNext; }
}
U0 DuelTick()
{
  if (duel_state==DUEL_PLAY && tS>=duel_deadline) DuelSubmit(TRUE);
}
U0 DuelStartGame()
{
  I64 i;
  duel_score=0; duel_streak=0; duel_best_streak=0; duel_idx=0;
  for (i=0;i<DUEL_NCH;i++) duel_pass[i]=-1;
  duel_state=DUEL_PLAY;
  DuelNext;
  DuelFlash("GO - NEW");
}
U0 DuelTypeChar(I64 c)
{
  I64 n;
  if (duel_state!=DUEL_PLAY) return;
  n=StrLen(duel_buf);
  if (n<58 && c>=32 && c<127) { duel_buf[n]=c; duel_buf[n+1]=0; }
}
U0 DuelBackspace()
{
  I64 n;
  if (duel_state!=DUEL_PLAY) return;
  n=StrLen(duel_buf);
  if (n>0) duel_buf[n-1]=0;
}
#endif
