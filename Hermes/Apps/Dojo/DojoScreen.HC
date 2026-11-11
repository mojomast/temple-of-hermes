#ifndef DOJO_SCREEN_HC
#define DOJO_SCREEN_HC
#include "DojoDraw.HC"
#include "DojoCheck.HC"
#include "DojoPop.HC"
I64 dojo_st[4],dojo_sc[4];
CDC *dojo_plate=NULL,*dojo_tek=NULL;
U8 *dojo_names[4]={"1 Caduceus draw","2 DolDoc form","3 draw_it sprite","4 File echo"};
U0 DojoLoadScores()
{
  I64 i;
  for (i=0;i<4;i++)
  {
    dojo_st[i]=DojoStatus(i+1);
    dojo_sc[i]=DojoScoreOf(i+1);
  }
}
#endif
