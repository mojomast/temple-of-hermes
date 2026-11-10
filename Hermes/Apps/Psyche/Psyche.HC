#define PSY_LAYERS		5
#define PSY_MAX_NODE		8
#define PSY_MAX_NODES		32
#define PSY_MAX_PULSES		48

class CPsyNode
{
  I64 num;
  F64 x,y;
  F64 act;
  F64 decay;
  F64 phase;
};

class CPsyPulse
{
  I64 layer;
  I64 from;
  I64 to;
  F64 t;
  F64 speed;
  I64 color;
};

static CPsyNode psy_nodes[PSY_MAX_NODES];
static I64 psy_layer_cnt[PSY_LAYERS]={4,6,8,6,3};
static I64 psy_layer_start[PSY_LAYERS+1];
static F64 psy_w[PSY_LAYERS-1][PSY_MAX_NODE][PSY_MAX_NODE];
static CPsyPulse psy_pulses[PSY_MAX_PULSES];
static CDC *psy_icon_dc=NULL;
static U8 *psy_icon_buf=NULL;
static F64 psy_t=0.0;
static I64 psy_frame=0;
static Bool psy_paused=FALSE;

U8 *PsyIconLoad()
{
  U8 *buf=FileRead("::/Hermes/Art/Icons/32/psyche.GR");
  if (!buf)
    return NULL;
  return buf;
}

U0 PsyIconInit()
{
  I64 x,y,c;
  psy_icon_buf=PsyIconLoad;
  psy_icon_dc=DCNew(64,64);
  DCFill(psy_icon_dc,BLACK);
  if (psy_icon_buf)
  {
    for (y=0;y<32;y++)
      for (x=0;x<32;x++)
      {
        c=psy_icon_buf[32+y*32+x]&15;
        if (c)
        {
          psy_icon_dc->color=c;
          GrRect(psy_icon_dc,x*2,y*2,2,2);
        }
      }
  }
}

U0 PsyRandEdge(I64 *layer,I64 *from,I64 *to)
{
  I64 l,a,b;
  l=RandU32()%(PSY_LAYERS-1);
  a=RandU32()%psy_layer_cnt[l];
  b=RandU32()%psy_layer_cnt[l+1];
  *layer=l;
  *from=psy_layer_start[l]+a;
  *to=psy_layer_start[l+1]+b;
}

U0 PsyResetPulse(CPsyPulse *p)
{
  PsyRandEdge(&p->layer,&p->from,&p->to);
  p->t=0.0;
  p->speed=0.008+0.020*Rand;
  if (RandU32()&1)
    p->color=LTCYAN;
  else
    p->color=LTPURPLE;
}

U0 PsyInit(I64 w,I64 h)
{
  I64 l,i,n,start=0;
  F64 dx,dy;
  for (l=0;l<PSY_LAYERS;l++)
  {
    psy_layer_start[l]=start;
    n=psy_layer_cnt[l];
    dx=w*0.13+l*(w*0.74)/(PSY_LAYERS-1);
    for (i=0;i<n;i++)
    {
      dy=h*0.52+(i-(n-1)/2.0)*(h*0.105);
      psy_nodes[start+i].num=start+i;
      psy_nodes[start+i].x=dx;
      psy_nodes[start+i].y=dy;
      psy_nodes[start+i].act=0.0;
      psy_nodes[start+i].decay=0.90+0.08*Rand;
      psy_nodes[start+i].phase=2.0*3.141592653589793*Rand;
    }
    start+=n;
  }
  psy_layer_start[PSY_LAYERS]=start;
  for (l=0;l<PSY_LAYERS-1;l++)
    for (i=0;i<psy_layer_cnt[l];i++)
      for (n=0;n<psy_layer_cnt[l+1];n++)
        psy_w[l][i][n]=Rand*2.0-1.0;
  for (i=0;i<PSY_MAX_PULSES;i++)
  {
    PsyResetPulse(&psy_pulses[i]);
    psy_pulses[i].t=Rand;
  }
  PsyIconInit;
}

U0 PsyStep()
{
  I64 l,i,n,start;
  F64 v,mx;
  psy_t+=0.016;
  start=0;
  for (l=0;l<PSY_LAYERS;l++)
  {
    n=psy_layer_cnt[l];
    if (!l)
    {
      for (i=0;i<n;i++)
        psy_nodes[i].act=0.50+0.50*Sin(psy_t*2.1+i*1.7);
    }
    else
    {
      for (i=0;i<n;i++)
      {
        psy_nodes[start+i].act*=psy_nodes[start+i].decay;
        mx=0.0;
        for (n=0;n<psy_layer_cnt[l-1];n++)
        {
          v=psy_nodes[psy_layer_start[l-1]+n].act*Abs(psy_w[l-1][n][i]);
          if (v>mx)
            mx=v;
        }
        if (mx>psy_nodes[start+i].act)
          psy_nodes[start+i].act=0.90*mx;
      }
    }
    start+=n;
  }
  for (i=0;i<PSY_MAX_PULSES;i++)
  {
    psy_pulses[i].t+=psy_pulses[i].speed;
    if (psy_pulses[i].t>=1.0)
    {
      PsyResetPulse(&psy_pulses[i]);
      psy_nodes[psy_pulses[i].to].act=1.0;
    }
  }
  psy_frame++;
}

U0 PsyDrawChart(CDC *dc,I64 x,I64 y,I64 w,I64 h)
{
  I64 i,px,py;
  F64 v;
  dc->color=DKGRAY;
  dc->thick=1;
  GrRect(dc,x,y,w,h);
  GrLine(dc,x,y+h/2,x+w,y+h/2);
  for (i=0;i<w;i++)
  {
    v=0.5+0.28*Sin(psy_t*0.9+i*0.06)+0.12*Sin(psy_t*2.7+i*0.021);
    if (v<0.03)
      v=0.03;
    if (v>0.97)
      v=0.97;
    py=y+h-2.0*(h-4.0)*v;
    px=x+i;
    if (i)
    {
      dc->color=LTCYAN;
      GrLine(dc,px-1,py,px,py);
    }
  }
  dc->color=LTGRAY;
  GrPrint(dc,x+5,y+5,"SIM LOSS");
  dc->color=WHITE;
  GrPrint(dc,x+w-13*8,y+h+4,"steps %d",psy_frame);
}

U0 PsyDraw(CDC *dc,I64 w,I64 h)
{
  I64 l,i,j,d;
  I64 px,py;
  CPsyNode *na,*nb;
  CPsyPulse *p;
  F64 u,v;
  DCFill(dc,BLACK);
  dc->thick=1;
  for (i=0;i<w;i+=32)
  {
    dc->color=8;
    GrLine(dc,i,0,i,h);
  }
  for (i=0;i<h;i+=32)
  {
    dc->color=8;
    GrLine(dc,0,i,w,i);
  }
  for (l=0;l<PSY_LAYERS-1;l++)
    for (i=0;i<psy_layer_cnt[l];i++)
      for (j=0;j<psy_layer_cnt[l+1];j++)
      {
        na=&psy_nodes[psy_layer_start[l]+i];
        nb=&psy_nodes[psy_layer_start[l+1]+j];
        if (Abs(psy_w[l][i][j])>0.72)
          dc->color=LTBLUE;
        else if (psy_w[l][i][j]>0.0)
          dc->color=BLUE;
        else
          dc->color=PURPLE;
        GrLine(dc,na->x,na->y,nb->x,nb->y);
      }
  for (i=0;i<PSY_MAX_PULSES;i++)
  {
    p=&psy_pulses[i];
    na=&psy_nodes[p->from];
    nb=&psy_nodes[p->to];
    u=p->t;
    px=na->x+(nb->x-na->x)*u;
    py=na->y+(nb->y-na->y)*u;
    dc->color=p->color;
    GrFillCircle(dc,px,py,0,5);
    v=u-0.07;
    if (v>0.0)
    {
      dc->color=LTBLUE;
      GrFillCircle(dc,na->x+(nb->x-na->x)*v,na->y+(nb->y-na->y)*v,0,3);
    }
  }
  for (i=0;i<PSY_MAX_NODES;i++)
  {
    na=&psy_nodes[i];
    d=13+9.0*na->act;
    dc->color=BLUE;
    GrFillCircle(dc,na->x,na->y,0,d+8);
    dc->color=LTBLUE;
    GrFillCircle(dc,na->x,na->y,0,d+3);
    if (na->act>0.75)
      dc->color=LTCYAN;
    else if (na->act>0.35)
      dc->color=CYAN;
    else
      dc->color=BLUE;
    GrFillCircle(dc,na->x,na->y,0,d);
    dc->color=WHITE;
    GrCircle(dc,na->x,na->y,(d+8)/2);
  }
  if (psy_icon_dc)
    GrBlot(dc,20,58,psy_icon_dc);
  dc->color=LTCYAN;
  GrPrint(dc,96,62,"PSYCHE");
  dc->color=LTGRAY;
  GrPrint(dc,96,78,"SIGNAL FIELD");
  dc->color=YELLOW;
  GrPrint(dc,96,94,"VISUALIZATION ONLY");
  dc->color=LTRED;
  GrPrint(dc,w-220,20,"NO NETWORK   NO TRAINING");
  dc->color=WHITE;
  GrPrint(dc,20,h-20,"SPACE pause   R reseed   ESC exit");
  dc->color=LTGREEN;
  GrPrint(dc,w-140,h-20,"FRAME %05d",psy_frame);
  PsyDrawChart(dc,w-210,h-140,180,80);
  if (psy_paused)
  {
    dc->color=YELLOW;
    GrPrint(dc,w/2-40,h/2,"PAUSED");
  }
}

public U0 Psyche()
{
  I64 ch,w,h,i;
  CDC *dc;
  SettingsPush;
  WinMax;
  DocClear;
  dc=DCAlias;
  w=Fs->pix_width;
  h=Fs->pix_height;
  PsyInit(w,h);
  try
  {
    while (TRUE)
    {
      ch=ScanChar;
      if (ch==CH_ESC||ch==CH_SHIFT_ESC)
        break;
      if (ch==CH_SPACE)
        psy_paused=!psy_paused;
      if (ch=='r'||ch=='R')
      {
        for (i=0;i<PSY_MAX_PULSES;i++)
          PsyResetPulse(&psy_pulses[i]);
        for (i=0;i<PSY_MAX_NODES;i++)
          psy_nodes[i].act=0.0;
        psy_frame=0;
        psy_t=0.0;
      }
      if (!psy_paused)
        PsyStep();
      PsyDraw(dc,w,h);
      Refresh;
      Sleep(20);
      Yield;
    }
  }
  catch
    PutExcept;
  if (psy_icon_dc)
  {
    DCDel(psy_icon_dc);
    psy_icon_dc=NULL;
  }
  Free(psy_icon_buf);
  psy_icon_buf=NULL;
  DCFill(dc);
  DCDel(dc);
  SettingsPop;
}
