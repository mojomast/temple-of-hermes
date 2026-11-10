#ifndef DOJO_SCORE_HC
#define DOJO_SCORE_HC
#include "DojoUtil.HC"
#include "DojoCmd.HC"
#include "DojoSmall.HC"
U8 DojoPix(CDC *dc,I64 x,I64 y)
{
  if (x<0||y<0||x>=dc->width||y>=dc->height) return 0;
  return dc->body[y*dc->width_internal+x]&15;
}
#endif
