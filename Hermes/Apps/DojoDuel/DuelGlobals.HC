#ifndef DUEL_GLOBALS_HC_V5
#define DUEL_GLOBALS_HC_V5
#define DUEL_NAME "DOJO DUEL"
#define DUEL_VER  "1.0"
#define DUEL_NCH  8
#define DUEL_TIME 12.0
#define DUEL_TITLE 0
#define DUEL_PLAY  1
#define DUEL_DONE  2
#define DUEL_URL "https://nousresearch.com/nouscoder-14b-a-competitive-olympiad-programming-model"
I64 duel_state=DUEL_TITLE,duel_idx=0,duel_score=0,duel_streak=0;
I64 duel_best_streak=0,duel_best=0,duel_beststreak=0,duel_runs=0;
I64 duel_pass[DUEL_NCH],duel_lastok=-1,duel_lastgain=0,duel_lasttime=0;
F64 duel_deadline=0,duel_startt=0;
U8 duel_buf[64],duel_flash[64];
CDC *duel_plate=NULL,*duel_bar=NULL,*duel_tek=NULL;
#endif
