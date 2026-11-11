U0 CadStep()
{
  I32 i,hx,hy,eat=-1;
  hx=cad_sx[0]+cad_ndx;
  hy=cad_sy[0]+cad_ndy;
  cad_dx=cad_ndx; cad_dy=cad_ndy;
  cad_ticks++;
  if (hx<0 || hx>=CAD_COLS || hy<0 || hy>=CAD_ROWS) {
    cad_alive=FALSE;
    return;
  }
  for (i=1;i<cad_len;i++)
    if (cad_sx[i]==hx && cad_sy[i]==hy) {
      cad_alive=FALSE;
      return;
    }
  for (i=0;i<CAD_FOOD;i++)
    if (cad_food[i] && cad_fx[i]==hx && cad_fy[i]==hy)
      eat=i;
  if (eat>=0) {
    if (cad_len<CAD_MAX) {
      for (i=cad_len;i>0;i--) {
        cad_sx[i]=cad_sx[i-1];
        cad_sy[i]=cad_sy[i-1];
      }
      cad_len++;
    } else {
      for (i=cad_len-1;i>0;i--) {
        cad_sx[i]=cad_sx[i-1];
        cad_sy[i]=cad_sy[i-1];
      }
    }
    cad_score+=10;
    cad_food[eat]=FALSE;
    CadFoodNew(eat);
    if (cad_sound) Snd(78);
    if (cad_score%50==0)
      StrCpy(cad_msg,"Southpaw (NEW): The offering is sweet.");
    else
      StrCpy(cad_msg,"Southpaw: Run it locally!");
  } else {
    for (i=cad_len-1;i>0;i--) {
      cad_sx[i]=cad_sx[i-1];
      cad_sy[i]=cad_sy[i-1];
    }
  }
  cad_sx[0]=hx;
  cad_sy[0]=hy;
  cad_delay=MaxI64(65,170-5*cad_len);
}

U0 CadEnd()
{
  if (cad_state==CAD_OVER) return;
  cad_state=CAD_OVER;
  CadSaveScore();
  StrCpy(cad_msg,"Southpaw (NEW): The serpent sleeps.");
  if (cad_sound) Snd(40);
}
