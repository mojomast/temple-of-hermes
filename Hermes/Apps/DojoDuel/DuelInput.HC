#ifndef DUEL_INPUT_HC_V5
#define DUEL_INPUT_HC_V5
#include "DuelState.HC"
#include "DuelResult.HC"
U0 DuelHandleKey(I64 k)
{
  U8 c=k;
  if (c=='p' || c=='P') { DuelPlaque; return; }
  if (duel_state==DUEL_TITLE)
  {
    if (c=='\n') DuelStartGame;
  }
  else if (duel_state==DUEL_PLAY)
  {
    if (c=='\n') DuelSubmit(FALSE);
    else if (c==CH_BACKSPACE) DuelBackspace;
    else if (c>=32 && c<127) DuelTypeChar(k);
  }
  else if (duel_state==DUEL_DONE)
  {
    if (c=='\n' || c=='r' || c=='R') DuelStartGame;
  }
}
#endif
