// Codex of Nous - a small lore browser for THE TEMPLE OF HERMES.
// It reads ::/Hermes/Lore/*.DD and *.TXT when that directory exists,
// otherwise it opens a bundled sample.  The art comes from
// Hermes/Art/Icons/32/codex-of-nous.GR.

Cd(__DIR__);;
#include "CodexArt"

#define CX_MAX        24
#define CX_MAX_LINES  256
#define CX_WRAP_COLS  48

U8 *cx_titles[CX_MAX];
U8 *cx_bodies[CX_MAX];
U8 *cx_sources[CX_MAX];
U8 *cx_lines[CX_MAX][CX_MAX_LINES];
I64 cx_line_cnt[CX_MAX];
I64 cx_cnt=0,cx_sel=0,cx_scroll=0,cx_list_top=0,cx_running=0;

U0 CxDrawArt(CDC *dc,I64 x,I64 y,I64 w,I64 h,U8 *img,I64 scale=1)
{
  I64 i,j,c;
  for (j=0;j<h;j++)
    for (i=0;i<w;i++)
    {
      c=img[j*w+i];
      if (c)
      {
        dc->color=c;
        GrRect(dc,x+i*scale,y+j*scale,scale,scale);
      }
    }
}

U8 *CxNameFromPath(U8 *path)
{
  I64 n=StrLen(path),s,e;
  U8 *res;
  while (n>0 && path[n-1]!='/')
    n--;
  s=n;
  e=StrLen(path);
  while (e>s && path[e-1]!='.')
    e--;
  if (e<=s)
    e=StrLen(path);
  res=MAlloc(e-s+1);
  MemCpy(res,path+s,e-s);
  res[e-s]=0;
  return res;
}

U0 CxWrap(I64 e)
{
  U8 *src=cx_bodies[e];
  U8 line[CX_WRAP_COLS+1];
  I64 i=0,n=0,col=0,start=0,last_space=-1,keep;
  U8 ch;
  if (!src)
  {
    cx_line_cnt[e]=0;
    return;
  }
  line[0]=0;
  while (src[i] && n<CX_MAX_LINES)
  {
    ch=src[i];
    if (ch=='\r')
      i++;
    else if (ch=='\n')
    {
      line[col]=0;
      cx_lines[e][n]=StrNew(line);
      n++;
      col=0;
      i++;
      start=i;
      last_space=-1;
    }
    else if (col>=CX_WRAP_COLS)
    {
      if (last_space>start)
      {
        keep=last_space-start;
        if (keep>CX_WRAP_COLS)
          keep=CX_WRAP_COLS;
        MemCpy(line,src+start,keep);
        line[keep]=0;
        cx_lines[e][n]=StrNew(line);
        n++;
        i=last_space+1;
        start=i;
        col=0;
        last_space=-1;
      }
      else
      {
        line[col]=0;
        cx_lines[e][n]=StrNew(line);
        n++;
        start=i;
        col=0;
        last_space=-1;
      }
    }
    else
    {
      line[col++]=ch;
      if (ch==' ')
        last_space=i;
      i++;
    }
  }
  if (col>0 && n<CX_MAX_LINES)
  {
    line[col]=0;
    cx_lines[e][n]=StrNew(line);
    n++;
  }
  cx_line_cnt[e]=n;
}

U0 CxAdd(U8 *title,U8 *body,U8 *source)
{
  if (cx_cnt>=CX_MAX)
    return;
  cx_titles[cx_cnt]=title;
  cx_bodies[cx_cnt]=body;
  cx_sources[cx_cnt]=source;
  CxWrap(cx_cnt);
  cx_cnt++;
}

#include "CodexLore"

U0 CxClear()
{
  I64 i,j;
  for (i=0;i<cx_cnt;i++)
  {
    Free(cx_titles[i]);
    Free(cx_bodies[i]);
    Free(cx_sources[i]);
    for (j=0;j<cx_line_cnt[i];j++)
      Free(cx_lines[i][j]);
  }
  cx_cnt=0;
  cx_sel=0;
  cx_scroll=0;
  cx_list_top=0;
}

I64 CxTryLore(U8 *mask)
{
  CDirEntry *head=NULL,*de;
  I64 found=0;
  CDoc *doc;
  U8 *txt;
  try
  {
    head=de=FilesFind(mask,FUF_JUST_FILES|FUF_CLUS_ORDER);
    while (de && cx_cnt<CX_MAX)
    {
      doc=DocRead(de->full_name,DOCF_NO_CURSOR);
      if (doc)
      {
        txt=DocDumpToStr(doc);
        DocDel(doc);
        if (txt && *txt)
        {
          CxAdd(CxNameFromPath(de->full_name),txt,StrNew(de->full_name));
          found++;
        }
        else if (txt)
          Free(txt);
      }
      de=de->next;
    }
  }
  catch
  {
  }
  if (head)
    DirTreeDel(head);
  return found;
}

U0 CxLoadAll()
{
  I64 found=0;
  CxClear;
  found+=CxTryLore("::/Hermes/Lore/*.DD");
  found+=CxTryLore("::/Hermes/Lore/*.TXT");
  if (!found)
    CxLoadSample;
  if (cx_cnt<=0)
    CxAdd(StrNew("Empty Codex"),StrNew("No lore entries were found.\n"),
          StrNew("built in"));
  if (cx_sel>=cx_cnt)
    cx_sel=cx_cnt-1;
}

I64 CxContentX(I64 w)
{
  I64 x=216;
  if (x>w-120)
    x=w-120;
  return x;
}

I64 CxListVisible(I64 h)
{
  I64 v=(h-108)/16;
  if (v<1)
    v=1;
  return v;
}

I64 CxBodyVisible(I64 h)
{
  I64 v=(h-124)/10;
  if (v<1)
    v=1;
  return v;
}

U0 CxClampScroll(I64 h)
{
  I64 max=cx_line_cnt[cx_sel]-CxBodyVisible(h)+1;
  if (max<1)
    max=1;
  if (cx_scroll<0)
    cx_scroll=0;
  if (cx_scroll>max-1)
    cx_scroll=max-1;
}

U0 CxDrawList(CDC *dc,I64 x,I64 y,I64 w,I64 h)
{
  I64 i,cy,vis=CxListVisible(h);
  dc->color=DKGRAY;
  GrRect(dc,x,y,w,h);
  dc->color=LTCYAN;
  GrPrint(dc,x+6,y+5,"ENTRIES");
  cy=y+22;
  if (cx_sel<cx_list_top)
    cx_list_top=cx_sel;
  if (cx_sel>=cx_list_top+vis)
    cx_list_top=cx_sel-vis+1;
  if (cx_list_top<0)
    cx_list_top=0;
  for (i=cx_list_top;i<cx_cnt && i<cx_list_top+vis;i++)
  {
    if (i==cx_sel)
    {
      dc->color=BLUE;
      GrRect(dc,x+4,cy-2,w-8,15);
      dc->color=WHITE;
    }
    else
      dc->color=LTGRAY;
    GrPrint(dc,x+8,cy,"%s",cx_titles[i]);
    cy+=16;
  }
}

U0 CxDrawBody(CDC *dc,I64 x,I64 y,I64 w,I64 h)
{
  I64 i,vis=CxBodyVisible(h),cy;
  dc->color=DKGRAY;
  GrRect(dc,x,y,w,h);
  dc->color=YELLOW;
  GrPrint(dc,x+8,y+5,"%s",cx_titles[cx_sel]);
  dc->color=LTGRAY;
  GrPrint(dc,x+8,y+20,"%d lines   scroll %d/%d",cx_line_cnt[cx_sel],
    cx_scroll+1,cx_line_cnt[cx_sel]);
  cy=y+38;
  for (i=cx_scroll;i<cx_line_cnt[cx_sel] && i<cx_scroll+vis;i++)
  {
    dc->color=WHITE;
    GrPrint(dc,x+8,cy,"%s",cx_lines[cx_sel][i]);
    cy+=10;
  }
  dc->color=CYAN;
  GrPrint(dc,x+8,y+h-15,"source: %s",cx_sources[cx_sel]);
}

U0 CxDrawIt(CTask *task,CDC *dc)
{
  I64 w=task->pix_width,h=task->pix_height;
  I64 cx=CxContentX(w);
  I64 list_w=cx-16;
  I64 body_w=w-cx-8;
  dc->color=BLACK;
  GrRect(dc,0,0,w,h);
  dc->color=PURPLE;
  GrRect(dc,0,0,w,72);
  CxDrawArt(dc,8,4,32,32,codex_icon,2);
  dc->color=YELLOW;
  GrPrint(dc,80,10,"CODEX OF NOUS");
  dc->color=LTCYAN;
  GrPrint(dc,80,26,"A browser for the lore of the temple");
  dc->color=LTGRAY;
  GrPrint(dc,80,44,"%d entries",cx_cnt);
  GrPrint(dc,w-110,44,"ESC quit");

  CxDrawList(dc,8,76,list_w,h-108);
  CxDrawBody(dc,cx,76,body_w,h-108);

  dc->color=DKGRAY;
  GrRect(dc,8,h-28,w-16,20);
  dc->color=LTGRAY;
  GrPrint(dc,14,h-23,
    "Up/Down select   PgUp/PgDn scroll   Home/End   Enter reload   Esc quit");
}

U0 Codex()
{
  I64 ch,sc,h;
  SettingsPush;
  Fs->text_attr=BLACK<<4+WHITE;
  MenuPush(
    "File {"
    "  Exit(,CH_ESC);"
    "}"
    "Codex {"
    "  Next(,,SC_CURSOR_DOWN);"
    "  Prev(,,SC_CURSOR_UP);"
    "  Reload(,'\n');"
    "}"
  );
  AutoComplete(0);
  WinBorder;
  WinMax;
  DocCursor;
  DocClear;
  CxLoadAll;
  cx_running=TRUE;
  Fs->draw_it=&CxDrawIt;
  h=Fs->pix_height;

  try
  {
    while (cx_running)
    {
      ch=GetKey(&sc);
      if (ch==CH_ESC || ch==CH_SHIFT_ESC)
        break;
      switch (ch)
      {
      case '\n':
        CxLoadAll;
        break;
      case '\t':
        cx_sel=(cx_sel+1)%cx_cnt;
        cx_scroll=0;
        break;
      default:
        switch (sc.u8[0])
        {
        case SC_CURSOR_UP:
          if (cx_sel>0)
            cx_sel--;
          cx_scroll=0;
          break;
        case SC_CURSOR_DOWN:
          if (cx_sel<cx_cnt-1)
            cx_sel++;
          cx_scroll=0;
          break;
        case SC_PAGE_UP:
          cx_scroll-=CxBodyVisible(h)-2;
          break;
        case SC_PAGE_DOWN:
          cx_scroll+=CxBodyVisible(h)-2;
          break;
        case SC_HOME:
          cx_scroll=0;
          break;
        case SC_END:
          cx_scroll=cx_line_cnt[cx_sel];
          break;
        }
      }
      CxClampScroll(h);
    }
  }
  catch
    PutExcept;

  cx_running=FALSE;
  Fs->draw_it=NULL;
  MenuPop;
  SettingsPop;
  DocClear;
  CxClear;
}

Codex;
