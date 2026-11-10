#define CAP_MAX_HEARTS		28

class CCapHeart
{
  F64 x,y,vy;
  I64 ttl;
  Bool live;
};

static F64 cap_x,cap_y,cap_vx;
static F64 cap_t;
static I64 cap_state,cap_timer,cap_blink,cap_blink_timer;
static I64 cap_mood,cap_hunger,cap_energy;
static I64 cap_last_lb;
static I64 cap_bubble;
static I64 cap_food;
static I64 cap_frame;
static CCapHeart cap_hearts[CAP_MAX_HEARTS];
static CDC *cap_icon_dc=NULL;
static U8 *cap_icon_buf=NULL;

U0 CapIconInit()
{
  I64 x,y,ic;
  cap_icon_buf=FileRead("::/Hermes/Art/Icons/32/capybara-pet.GR");
  cap_icon_dc=DCNew(64,64);
  DCFill(cap_icon_dc,BLACK);
  if (cap_icon_buf)
  {
    for (y=0;y<32;y++)
      for (x=0;x<32;x++)
      {
        ic=cap_icon_buf[32+y*32+x]&15;
        if (ic)
        {
          cap_icon_dc->color=ic;
          GrRect(cap_icon_dc,x*2,y*2,2,2);
        }
      }
  }
}

U0 CapFillElli(CDC *dc,I64 cx,I64 cy,I64 rx,I64 ry,I64 color)
{
  I64 y,dx;
  F64 q,yy,rr;
  dc->color=color;
  dc->thick=1;
  for (y=-ry;y<=ry;y++)
  {
    yy=y;
    rr=ry;
    q=1.0-(yy*yy)/(rr*rr);
    if (q<0.0)
      q=0.0;
    dx=rx*Sqrt(q);
    GrLine(dc,cx-dx,cy+y,cx+dx,cy+y);
  }
}

U0 CapSpawnHeart(I64 x,I64 y)
{
  I64 i;
  for (i=0;i<CAP_MAX_HEARTS;i++)
    if (!cap_hearts[i].live)
    {
      cap_hearts[i].live=TRUE;
      cap_hearts[i].x=x+(RandU32()%40)-20;
      cap_hearts[i].y=y;
      cap_hearts[i].vy=0.8+0.9*Rand;
      cap_hearts[i].ttl=45+RandU32()%30;
      return;
    }
}

U0 CapPet()
{
  cap_mood+=8;
  if (cap_mood>100)
    cap_mood=100;
  cap_state=3;
  cap_timer=70;
  cap_bubble=120;
  CapSpawnHeart(cap_x+40,cap_y-90);
  CapSpawnHeart(cap_x+80,cap_y-96);
}

U0 CapFeed()
{
  cap_hunger+=22;
  if (cap_hunger>100)
    cap_hunger=100;
  cap_state=3;
  cap_timer=90;
  cap_food=150;
  cap_bubble=100;
}

Bool CapHit(I64 mx,I64 my)
{
  F64 dx,dy;
  dx=(mx-(cap_x+35))/95.0;
  dy=(my-(cap_y+20))/80.0;
  return dx*dx+dy*dy<=1.0;
}

U0 CapInit(I64 w,I64 h)
{
  I64 i;
  cap_x=w*0.35;
  cap_y=h*0.58;
  cap_vx=1.0;
  cap_t=0.0;
  cap_state=0;
  cap_timer=160;
  cap_blink=0;
  cap_blink_timer=90;
  cap_mood=72;
  cap_hunger=68;
  cap_energy=84;
  cap_last_lb=0;
  cap_bubble=0;
  cap_food=0;
  cap_frame=0;
  for (i=0;i<CAP_MAX_HEARTS;i++)
    cap_hearts[i].live=FALSE;
  CapIconInit;
}

U0 CapStep(I64 w,I64 h)
{
  I64 i,r;
  F64 margin;
  cap_t+=0.05;
  cap_frame++;
  cap_timer--;
  if (cap_timer<=0)
  {
    r=RandU32()%100;
    if (cap_state==2)
    {
      cap_state=0;
      cap_timer=120;
    }
    else if (r<45)
    {
      cap_state=1;
      cap_timer=90+RandU32()%120;
      if (RandU32()&1)
        cap_vx=1.15;
      else
        cap_vx=-1.15;
    }
    else if (r<70)
    {
      cap_state=0;
      cap_timer=80+RandU32()%100;
    }
    else if (r<88)
    {
      cap_state=2;
      cap_timer=160+RandU32()%200;
      cap_energy+=6;
    }
    else
    {
      cap_state=3;
      cap_timer=70;
    }
  }
  if (cap_state==1)
  {
    cap_x+=cap_vx;
    margin=140.0;
    if (cap_x<margin)
    {
      cap_x=margin;
      cap_vx=Abs(cap_vx);
    }
    if (cap_x>w-margin)
    {
      cap_x=w-margin;
      cap_vx=-Abs(cap_vx);
    }
    cap_energy-=0.03;
  }
  if (cap_y>h-150)
    cap_y=h-150;
  if (cap_state==2)
    cap_energy+=0.02;
  if (cap_hunger>0 && (cap_frame&3)==0)
    cap_hunger-=0.01;
  if (cap_mood>0 && (cap_frame&7)==0)
    cap_mood-=0.01;
  cap_blink_timer--;
  if (cap_blink_timer<=0)
  {
    cap_blink=8;
    cap_blink_timer=80+RandU32()%160;
  }
  if (cap_blink>0)
    cap_blink--;
  if (cap_bubble>0)
    cap_bubble--;
  if (cap_food>0)
    cap_food--;
  for (i=0;i<CAP_MAX_HEARTS;i++)
    if (cap_hearts[i].live)
    {
      cap_hearts[i].y-=cap_hearts[i].vy;
      cap_hearts[i].ttl--;
      if (cap_hearts[i].ttl<=0)
        cap_hearts[i].live=FALSE;
    }
}

U0 CapDrawHeart(CDC *dc,I64 x,I64 y,I64 color)
{
  dc->color=color;
  GrFillCircle(dc,x-5,y-3,0,10);
  GrFillCircle(dc,x+5,y-3,0,10);
  GrLine(dc,x-9,y,x,y+11);
  GrLine(dc,x+9,y,x,y+11);
  GrLine(dc,x-7,y+2,x,y+11);
  GrLine(dc,x+7,y+2,x,y+11);
}

U0 CapDrawScene(CDC *dc,I64 w,I64 h)
{
  I64 i,x,y,horizon,grass;
  F64 bob;
  I64 cx,cy,leg,hx,hy;
  horizon=h*0.62;
  grass=h-horizon;
  DCFill(dc,BLACK);
  dc->thick=1;
  dc->color=BLUE;
  GrRect(dc,0,0,w,horizon);
  for (y=0;y<horizon;y+=24)
  {
    dc->color=LTBLUE;
    GrRect(dc,0,y,w,2);
  }
  dc->color=YELLOW;
  GrFillCircle(dc,w-90,70,0,64);
  dc->color=LTGRAY;
  GrFillCircle(dc,w-82,64,0,54);
  dc->color=WHITE;
  GrFillCircle(dc,w-112,108,0,58);
  GrFillCircle(dc,w-70,116,0,48);
  GrFillCircle(dc,w-148,116,0,38);
  dc->color=LTCYAN;
  GrFillCircle(dc,150,96,0,46);
  GrFillCircle(dc,190,104,0,38);
  GrFillCircle(dc,112,108,0,34);
  dc->color=GREEN;
  CapFillElli(dc,70,horizon+8,260,90,GREEN);
  CapFillElli(dc,w-90,horizon+4,300,80,GREEN);
  dc->color=LTGREEN;
  GrRect(dc,0,horizon,w,grass);
  for (i=0;i<900;i++)
  {
    x=(i*173+37)%w;
    y=horizon+((i*61+11)%(grass-4));
    dc->color=GREEN;
    GrLine(dc,x,y,x+1,y-5);
  }
  for (i=0;i<26;i++)
  {
    x=(i*97+51)%w;
    y=h-8-((i*31)%26);
    dc->color=LTGREEN;
    GrLine(dc,x,y,x-4,y-12);
    GrLine(dc,x,y,x+2,y-14);
    GrLine(dc,x,y,x+6,y-10);
  }
  dc->color=DKGRAY;
  GrRect(dc,0,h-4,w,4);
  bob=Sin(cap_t*2.2)*4.0;
  if (cap_state==1)
    bob=Abs(Sin(cap_t*8.0))*6.0;
  if (cap_state==2)
    bob=2.0;
  cx=cap_x;
  cy=cap_y+bob;
  dc->color=BLACK;
  CapFillElli(dc,cx+35,cy+86,128,22,BLACK);
  for (i=0;i<4;i++)
  {
    leg=cx-35+i*35;
    if (cap_state==1)
      leg+=6.0*Sin(cap_t*8.0+i*1.7);
    dc->color=BROWN;
    GrRect(dc,leg,cy+38,22,54);
    dc->color=DKGRAY;
    GrRect(dc,leg-2,cy+84,26,10);
  }
  CapFillElli(dc,cx+40,cy,96,62,BROWN);
  CapFillElli(dc,cx+28,cy+18,78,38,BROWN);
  CapFillElli(dc,cx+18,cy+26,60,24,YELLOW);
  CapFillElli(dc,cx+105,cy-38,52,44,BROWN);
  CapFillElli(dc,cx+122,cy-18,38,28,YELLOW);
  CapFillElli(dc,cx+56,cy-82,15,14,BROWN);
  CapFillElli(dc,cx+56,cy-82,7,7,LTRED);
  CapFillElli(dc,cx+102,cy-84,15,14,BROWN);
  CapFillElli(dc,cx+102,cy-84,7,7,LTRED);
  dc->color=BLACK;
  if (cap_state==2 || cap_blink)
  {
    GrLine(dc,cx+76,cy-62,cx+90,cy-62);
    GrLine(dc,cx+112,cy-64,cx+126,cy-64);
  }
  else
  {
    GrFillCircle(dc,cx+83,cy-63,0,8);
    GrFillCircle(dc,cx+119,cy-65,0,8);
    dc->color=WHITE;
    GrFillCircle(dc,cx+85,cy-65,0,3);
    GrFillCircle(dc,cx+121,cy-67,0,3);
  }
  dc->color=BLACK;
  GrFillCircle(dc,cx+140,cy-27,0,8);
  dc->color=LTRED;
  GrFillCircle(dc,cx+74,cy-40,0,10);
  GrFillCircle(dc,cx+111,cy-42,0,10);
  dc->color=DKGRAY;
  GrLine(dc,cx+140,cy-18,cx+140,cy-8);
  GrLine(dc,cx+140,cy-8,cx+132,cy-2);
  dc->color=BROWN;
  GrFillCircle(dc,cx+58,cy-112,0,9);
  GrFillCircle(dc,cx+103,cy-114,0,9);
  if (cap_state==2)
  {
    dc->color=LTCYAN;
    for (i=0;i<3;i++)
      GrPrint(dc,cx+150+i*10,cy-115-i*18,"z");
  }
  if (cap_food>0)
  {
    dc->color=LTGREEN;
    GrFillCircle(dc,cx+152,cy-2,0,8);
    GrFillCircle(dc,cx+162,cy-6,0,7);
    dc->color=DKGRAY;
    GrLine(dc,cx+150,cy+2,cx+140,cy+14);
  }
  for (i=0;i<CAP_MAX_HEARTS;i++)
  {
    if (cap_hearts[i].live)
    {
      if (cap_hearts[i].ttl>=15)
      {
        hx=cap_hearts[i].x;
        hy=cap_hearts[i].y;
        if (cap_hearts[i].ttl>20)
          CapDrawHeart(dc,hx,hy,LTRED);
        else
          CapDrawHeart(dc,hx,hy,LTPURPLE);
      }
    }
  }
}

U0 CapDrawHud(CDC *dc,I64 w,I64 h)
{
  I64 i;
  dc->color=BLACK;
  GrRect(dc,0,0,w,26);
  if (cap_icon_dc)
    GrBlot(dc,8,4,cap_icon_dc);
  dc->color=LTCYAN;
  GrPrint(dc,80,7,"CAPYBARA");
  dc->color=LTGRAY;
  GrPrint(dc,80,17,"temple pet / TinkerOS");
  dc->color=WHITE;
  GrPrint(dc,260,7,"MOOD");
  GrPrint(dc,380,7,"FULL");
  GrPrint(dc,480,7,"ENERGY");
  dc->color=DKGRAY;
  GrRect(dc,260,17,90,7);
  GrRect(dc,380,17,90,7);
  GrRect(dc,480,17,90,7);
  dc->color=LTRED;
  GrRect(dc,261,18,88*cap_mood/100,5);
  dc->color=YELLOW;
  GrRect(dc,381,18,88*cap_hunger/100,5);
  dc->color=LTGREEN;
  GrRect(dc,481,18,88*cap_energy/100,5);
  dc->color=YELLOW;
  GrPrint(dc,20,h-20,"F feed   P pet   S sleep   LEFT-CLICK pet   ESC exit");
  if (cap_bubble>0)
  {
    i=w/2-60;
    dc->color=WHITE;
    GrPrint(dc,i,120,"capy happy!");
    dc->color=LTRED;
    CapDrawHeart(dc,i+150,116,LTRED);
  }
  if (cap_state==2)
  {
    dc->color=LTCYAN;
    GrPrint(dc,w/2-40,150,"capy nap");
  }
}

public U0 Capybara()
{
  I64 ch,w,h,mx,my,lb;
  CDC *dc;
  SettingsPush;
  WinMax;
  DocClear;
  dc=DCAlias;
  w=Fs->pix_width;
  h=Fs->pix_height;
  CapInit(w,h);
  try
  {
    while (TRUE)
    {
      ch=ScanChar;
      if (ch==CH_ESC||ch==CH_SHIFT_ESC)
        break;
      if (ch=='f'||ch=='F')
        CapFeed;
      if (ch=='p'||ch=='P')
        CapPet;
      if (ch=='s'||ch=='S')
      {
        if (cap_state==2)
        {
          cap_state=0;
          cap_timer=90;
        }
        else
        {
          cap_state=2;
          cap_timer=240;
        }
      }
      lb=ms.lb;
      if (lb && !cap_last_lb)
      {
        mx=ms.pos.x-Fs->pix_left-Fs->scroll_x;
        my=ms.pos.y-Fs->pix_top-Fs->scroll_y;
        if (CapHit(mx,my))
          CapPet;
      }
      cap_last_lb=lb;
      CapStep(w,h);
      CapDrawScene(dc,w,h);
      CapDrawHud(dc,w,h);
      Refresh;
      Sleep(33);
      Yield;
    }
  }
  catch
    PutExcept;
  if (cap_icon_dc)
  {
    DCDel(cap_icon_dc);
    cap_icon_dc=NULL;
  }
  Free(cap_icon_buf);
  cap_icon_buf=NULL;
  DCFill(dc);
  DCDel(dc);
  SettingsPop;
}
