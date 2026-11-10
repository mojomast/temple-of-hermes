// Southpaw DolDoc view.  All post text is passed through SouthpawSafeText
// before it reaches DocPrint, so a post can never inject a DolDoc command.
// No side effects at load time.

#ifndef SOUTHP_VIEW
#define SOUTHP_VIEW

U0 SouthpawRender(CDoc *doc,CSouthpawPost *head,U8 *channel,I64 count,I64 agents)
{
  CSouthpawPost *p;
  U8 *safe;
  U8 *last_section;
  last_section=NULL;

  DocPrint(doc,"$$FG,YELLOW$$SOUTHPAW$$FG$$\n");
  DocPrint(doc,"$$FG,LTBLUE$$BBS highlights, announced$$FG$$\n\n");
  if (FileFind(SP_PLATE,,FUF_JUST_FILES))
    DocGR(doc,SP_PLATE);
  else
    DocPrint(doc,"$$FG,CYAN$$[Southpaw header plate not installed]$$FG$$\n");
  if (FileFind(SP_ICON64,,FUF_JUST_FILES))
  {
    DocGR(doc,SP_ICON64);
    DocPrint(doc," ");
  }
  if (FileFind(SP_ICON32,,FUF_JUST_FILES))
  {
    DocGR(doc,SP_ICON32);
    DocPrint(doc," ");
  }
  // NEW announcer line.
  DocPrint(doc,"$$FG,LTGREEN$$Run it locally! Here is the board, distilled.$$FG$$\n\n");
  safe=SouthpawSafeText(channel);
  DocPrint(doc,"$$FG,LTCYAN$$Channel:$$FG$$ %s\n",SouthpawDft(safe,"BBS"));
  Free(safe);
  DocPrint(doc,"$$FG,LTCYAN$$Posts:$$FG$$ %d    $$FG,LTCYAN$$Agent posts:$$FG$$ %d\n",count,agents);
  // NEW announcer line.
  DocPrint(doc,"$$FG,DKGRAY$$Agent posts are always labeled. Bodies are text, never code.$$FG$$\n");
  p=head;
  while (p)
  {
    if (!last_section || StrCmp(last_section,p->section))
    {
      safe=SouthpawSafeText(p->section);
      DocPrint(doc,"\n$$FG,WHITE$$== %s ==$$FG$$\n",
	       SouthpawDft(safe,"Highlights"));
      Free(safe);
      last_section=p->section;
    }
    safe=SouthpawSafeText(p->subject);
    DocPrint(doc,"\n$$FG,YELLOW$$--- %s ---$$FG$$\n",
	     SouthpawDft(safe,"(no subject)"));
    Free(safe);
    if (FileFind(SP_ICON16,,FUF_JUST_FILES))
    {
      DocGR(doc,SP_ICON16);
      DocPrint(doc," ");
    }
    if (StrIMatch(p->kind,"agent"))
      DocPrint(doc,"$$FG,LTRED$$[AGENT POST]$$FG$$ ");
    else
    {
      safe=SouthpawSafeText(p->kind);
      DocPrint(doc,"$$FG,LTBLUE$$[%s]$$FG$$ ",SouthpawDft(safe,"POST"));
      Free(safe);
    }
    safe=SouthpawSafeText(p->author);
    DocPrint(doc,"$$FG,LTGREEN$$%s$$FG$$",SouthpawDft(safe,"unknown"));
    Free(safe);
    safe=SouthpawSafeText(p->when);
    DocPrint(doc,"$$FG,DKGRAY$$  %s$$FG$$\n",safe);
    Free(safe);
    safe=SouthpawSafeText(p->body);
    DocPrint(doc,"%s\n",safe);
    Free(safe);
    p=p->next;
  }
  // NEW announcer line.
  DocPrint(doc,"\n$$FG,DKGRAY$$Southpaw is a face on the board, not a second protocol.$$FG$$\n");
}

U0 SouthpawView()
{
  I64 count;
  I64 agents;
  U8 *channel;
  U8 *path;
  count=0;
  agents=0;
  channel=NULL;
  CSouthpawPost *head;
  CDoc *doc;

  path=SouthpawFixturePath();
  head=SouthpawParseFile(path,&count,&agents,&channel);
  doc=DocNew;
  StrCpy(doc->filename.name,SP_NAME);
  SouthpawRender(doc,head,channel,count,agents);
  SouthpawPostsDel(head);
  Free(channel);
  PopUpViewDoc(doc,DOF_WIN_MAX);
}


#endif
