#ifndef HERMES_OFFERINGS_DRAW_HC
#define HERMES_OFFERINGS_DRAW_HC

#define OFFER_CELL_W 156
#define OFFER_CELL_H 76
#define OFFER_GRID_X 8
#define OFFER_GRID_Y 204

U0 OfferDrawCatIcon(CDC *dc,I64 x,I64 y,I64 cat)
{
  if (cat==OFFER_WALL)
  {
    dc->color=LTBLUE;
    GrRect(dc,x,y,24,24);
    dc->color=BLUE;
    GrRect(dc,x+3,y+3,18,18);
    dc->color=LTCYAN;
    GrRect(dc,x+6,y+6,12,12);
    dc->color=YELLOW;
    GrRect(dc,x+15,y+4,5,5);
  }
  else if (cat==OFFER_PAL)
  {
    dc->color=RED;
    GrRect(dc,x,y,11,11);
    dc->color=GREEN;
    GrRect(dc,x+13,y,11,11);
    dc->color=BLUE;
    GrRect(dc,x,y+13,11,11);
    dc->color=YELLOW;
    GrRect(dc,x+13,y+13,11,11);
  }
  else
  {
    dc->color=DKGRAY;
    GrRect(dc,x,y,24,24);
    dc->color=LTGREEN;
    GrRect(dc,x+4,y+5,16,2);
    GrRect(dc,x+4,y+11,12,2);
    GrRect(dc,x+4,y+17,16,2);
  }
}

U0 OfferDrawShop(CTask *task,CDC *dc,COfferUI *s)
{
  I64 i,col,row,x,y;
  COfferItem *it;
  if (s->plate)
    GrBlot(dc,0,0,s->plate);
  else
  {
    dc->color=PURPLE;
    GrRect(dc,0,0,task->pix_width,160);
    dc->color=YELLOW;
    GrPrint(dc,16,24,"DON PIEDRO'S OFFERINGS");
  }
  dc->color=BLACK;
  GrRect(dc,8,8,320,46);
  dc->color=YELLOW;
  GrPrint(dc,16,12,"DON PIEDRO'S OFFERINGS");
  dc->color=WHITE;
  GrPrint(dc,16,26,"Hello I Hermes biggest fanboi");
  dc->color=LTCYAN;
  GrPrint(dc,16,40,"Spoons only. No real money.");

  if (s->piedro)
    GrBlot(dc,8,168,s->piedro);
  else
  {
    dc->color=BROWN;
    GrRect(dc,8,168,32,32);
  }
  dc->color=YELLOW;
  GrPrint(dc,48,170,"DON PIEDRO'S TABLE");
  dc->color=LTGRAY;
  GrPrint(dc,48,184,"Wallpapers, palettes and HolyC snippets");

  for (i=0;i<offer_count;i++)
  {
    it=&offer_items[i];
    col=i%4;
    row=i/4;
    x=OFFER_GRID_X+col*OFFER_CELL_W;
    y=OFFER_GRID_Y+row*OFFER_CELL_H;
    dc->color=DKGRAY;
    GrRect(dc,x+2,y,OFFER_CELL_W-6,OFFER_CELL_H-4);
    if (i==s->selected)
    {
      dc->color=YELLOW;
      GrBorder(dc,x,y-1,x+OFFER_CELL_W-5,y+OFFER_CELL_H-5,1,0);
    }
    OfferDrawCatIcon(dc,x+6,y+6,it->cat);
    if (i==s->selected)
      dc->color=YELLOW;
    else
      dc->color=WHITE;
    GrPrint(dc,x+34,y+7,"%s",it->title);
    dc->color=LTGREEN;
    if (it->price>0)
      GrPrint(dc,x+6,y+56,"%d spoons",it->price);
    else
      GrPrint(dc,x+6,y+56,"free");
    if (it->is_new)
    {
      dc->color=RED;
      GrRect(dc,x+116,y+6,32,11);
      dc->color=YELLOW;
      GrPrint(dc,x+120,y+8,"NEW");
    }
    if (it->installed)
    {
      dc->color=LTCYAN;
      GrPrint(dc,x+6,y+44,"installed");
    }
    else
    {
      dc->color=LTGRAY;
      GrPrint(dc,x+6,y+44,"%s",OfferCatName(it->cat));
    }
  }
  dc->color=LTGRAY;
  if (s->status)
    GrPrint(dc,8,438,"%s",s->status);
  dc->color=BLACK;
  GrRect(dc,0,452,task->pix_width,28);
  dc->color=LTGRAY;
  GrPrint(dc,8,456,"Up/Down select   Enter preview+install   L list   G get   I install   Esc quit");
  dc->color=LTCYAN;
  GrPrint(dc,8,468,"Spoons are pretend. No real money.");
}

U0 OfferDrawWallPreview(CTask *task,CDC *dc,COfferUI *s)
{
  COfferItem *it=&offer_items[s->selected];
  if (s->wall)
    GrBlot(dc,0,0,s->wall);
  else
  {
    dc->color=BLACK;
    GrRect(dc,0,0,task->pix_width,task->pix_height);
  }
  dc->color=BLACK;
  GrRect(dc,0,0,task->pix_width,22);
  dc->color=YELLOW;
  GrPrint(dc,8,7,"WALLPAPER: %s   Esc back",it->title);
  dc->color=BLACK;
  GrRect(dc,0,task->pix_height-22,task->pix_width,22);
  dc->color=WHITE;
  GrPrint(dc,8,task->pix_height-15,"Installed to %s   Esc back",it->dest);
}

U0 OfferDrawSnippetPreview(CTask *task,CDC *dc,COfferUI *s)
{
  U8 line[80],ch;
  I64 i=0,col=0,y=34;
  U8 *txt=s->snippet_text;
  dc->color=BLACK;
  GrRect(dc,0,0,task->pix_width,task->pix_height);
  dc->color=BLUE;
  GrRect(dc,0,0,task->pix_width,24);
  dc->color=YELLOW;
  GrPrint(dc,8,8,"SNIPPET: %s",OfferOrEmpty(s->snippet_name));
  dc->color=WHITE;
  GrPrint(dc,task->pix_width-80,8,"Esc back");
  if (txt)
  {
    while (txt[i] && y<448)
    {
      ch=txt[i++];
      if (ch=='\r')
        ;
      else if (ch=='\n')
      {
        line[col]=0;
        dc->color=LTCYAN;
        GrPrint(dc,8,y,"%s",line);
        y+=10;
        col=0;
      }
      else
      {
        if (ch=='\t')
          ch=' ';
        if (col<76)
          line[col++]=ch;
      }
    }
    if (col && y<448)
    {
      line[col]=0;
      dc->color=LTCYAN;
      GrPrint(dc,8,y,"%s",line);
    }
  }
  else
  {
    dc->color=LTRED;
    GrPrint(dc,8,40,"Snippet file not found on this image.");
  }
  dc->color=BLACK;
  GrRect(dc,0,task->pix_height-22,task->pix_width,22);
  dc->color=LTGRAY;
  GrPrint(dc,8,task->pix_height-15,"Esc back to the shop   I installs this pack");
}

U0 OfferDrawPalettePreview(CTask *task,CDC *dc,COfferUI *s)
{
  I64 i,col,row,x,y;
  COfferItem *it=&offer_items[s->selected];
  dc->color=BLACK;
  GrRect(dc,0,0,task->pix_width,task->pix_height);
  dc->color=BLUE;
  GrRect(dc,0,0,task->pix_width,24);
  dc->color=YELLOW;
  GrPrint(dc,8,8,"PALETTE: %s",it->title);
  dc->color=WHITE;
  GrPrint(dc,task->pix_width-80,8,"Esc back");
  for (i=0;i<16;i++)
  {
    col=i%4;
    row=i/4;
    x=32+col*150;
    y=44+row*100;
    dc->color=i;
    GrRect(dc,x,y,128,56);
    dc->color=WHITE;
    GrBorder(dc,x-1,y-1,x+128,y+56,1,0);
    GrPrint(dc,x,y+62,"%d %s",i,offer_pal_name[i]);
  }
  dc->color=BLACK;
  GrRect(dc,0,task->pix_height-22,task->pix_width,22);
  dc->color=LTGRAY;
  GrPrint(dc,8,task->pix_height-15,"Esc back to the shop   I installs this palette card");
}

U0 OfferingsDraw(CTask *task,CDC *dc)
{
  COfferUI *s=task->user_data(COfferUI *);
  if (!s)
    return;
  if (s->mode==OFFER_MODE_WALL)
    OfferDrawWallPreview(task,dc,s);
  else if (s->mode==OFFER_MODE_SNIP)
    OfferDrawSnippetPreview(task,dc,s);
  else if (s->mode==OFFER_MODE_PAL)
    OfferDrawPalettePreview(task,dc,s);
  else
    OfferDrawShop(task,dc,s);
}

#endif
