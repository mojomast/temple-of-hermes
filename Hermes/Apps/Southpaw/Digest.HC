// SouthpawDigest: read a local digest, write a plain-text result file.
// This is the agent-facing path; it never scrapes the screen.
// No side effects at load time.

#ifndef SOUTHP_DIGEST
#define SOUTHP_DIGEST

U0 SouthpawDigest(U8 *digest_path=NULL,U8 *out_path=NULL)
{
  I64 count;
  I64 agents;
  U8 *channel;
  U8 *ch;
  U8 *out;
  U8 *next;
  U8 *safe;
  CSouthpawPost *head;
  CSouthpawPost *p;
  count=0;
  agents=0;
  channel=NULL;

  if (!digest_path)
    digest_path=SouthpawFixturePath();
  if (!out_path)
    out_path=SP_RESULT;
  head=SouthpawParseFile(digest_path,&count,&agents,&channel);
  if (channel && *channel)
    ch=channel;
  else
    ch="BBS";
  out=MStrPrint("SouthpawDigest 1\nchannel: %s\nposts: %d\nagent_posts: %d\n",
		ch,count,agents);
  p=head;
  while (p)
  {
    out=SouthpawCatField(out,"id: ",p->id);
    out=SouthpawCatField(out,"from: ",p->author);
    out=SouthpawCatField(out,"kind: ",p->kind);
    out=SouthpawCatField(out,"time: ",p->when);
    out=SouthpawCatField(out,"section: ",p->section);
    out=SouthpawCatField(out,"subject: ",p->subject);
    safe=SouthpawSafeText(p->body);
    next=MStrPrint("%sbody:\n%s\n",out,safe);
    Free(out); Free(safe); out=next;
    p=p->next;
  }
  FileWrite(out_path,out,StrLen(out));
  Free(out);
  SouthpawPostsDel(head);
  Free(channel);
  "%s: %d posts (%d agent) -> %s\n",SP_NAME,count,agents,out_path;
}


#endif
