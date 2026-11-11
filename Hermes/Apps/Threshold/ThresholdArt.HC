CDC *th_header=NULL,*th_icon=NULL,*th_splash=NULL;
Bool th_art_tried=FALSE;

U0 ThresholdLoadArt()
{//Load the small header plate and Nous Girl icon once.
  U8 *p;
  if (th_art_tried)
    return;
  th_art_tried=TRUE;
  p=ThresholdArtFile(TH_ART_HEADER);
  th_header=GRRead(p);
  Free(p);
  if (th_header)
    th_header->flags|=DCF_NO_TRANSPARENTS;
  p=ThresholdArtFile(TH_ART_ICON);
  th_icon=GRRead(p);
  Free(p);
  if (th_icon)
    th_icon->flags|=DCF_NO_TRANSPARENTS;
}

U0 ThresholdFreeArt()
{//Release every art DC, including a resident splash.
  if (th_header)
  {
    DCDel(th_header);
    th_header=NULL;
  }
  if (th_icon)
  {
    DCDel(th_icon);
    th_icon=NULL;
  }
  if (th_splash)
  {
    DCDel(th_splash);
    th_splash=NULL;
  }
  th_art_tried=FALSE;
}

U0 ThresholdSplashToggle()
{//At most one 640x480 GR is resident: the splash, only while viewed.
  U8 *p;
  if (th_splash)
  {
    DCDel(th_splash);
    th_splash=NULL;
    return;
  }
  p=ThresholdArtFile(TH_ART_SPLASH);
  th_splash=GRRead(p);
  Free(p);
  if (th_splash)
    th_splash->flags|=DCF_NO_TRANSPARENTS;
}
