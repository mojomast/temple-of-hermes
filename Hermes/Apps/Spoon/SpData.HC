#ifndef SP_DATA_HC
#define SP_DATA_HC

#define SP_MAX 12
#define SP_TOSSES 18
#define SP_AGENT_TOSSES 12

#define SP_KIND_WALL 0
#define SP_KIND_SNIP 1
#define SP_KIND_PAL 2
#define SP_KIND_NEW 3

#define SP_PLAY_TOP 180
#define SP_PLAY_BOT 450
#define SP_SPOON_Y 416
#define SP_G 240.0
#define SP_SPOON_MIN 48.0
#define SP_SPOON_MAX 592.0

class COffer
{
  Bool active;
  I64 kind;
  F64 x,y,vx,vy;
  F64 spin;
};

class CSpoon
{
  COffer offers[SP_MAX];
  F64 spoon_x;
  I64 caught,missed,score,high,tosses,flash;
  Bool over,started,agent;
  F64 t,next_toss,over_at;
  CDC *plate;
  CDC *piedro;
};

#endif
