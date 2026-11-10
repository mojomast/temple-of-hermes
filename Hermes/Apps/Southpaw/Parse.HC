// Southpaw digest parser.  The digest is DATA.  Nothing in a post body
// is ever compiled or executed; bodies are copied into display strings.
// No side effects at load time.

#ifndef SOUTHP_PARSE
#define SOUTHP_PARSE

U8 *SouthpawTrim(U8 *st)
{
  U8 *end;
  while (*st==' ' || *st=='\t')
    st++;
  end=st+StrLen(st);
  while (end>st && (end[-1]==' ' || end[-1]=='\t' || end[-1]=='\r'))
  {
    end--;
    *end=0;
  }
  return st;
}

U8 *SouthpawSafeText(U8 *src)
{
  I64 i,len;
  U8 *res;
  U8 *d;
  U8 c;
  if (!src)
    src="";
  len=StrLen(src);
  res=MAlloc(len+1);
  d=res;
  for (i=0; i<len; i++)
  {
    c=src[i];
    if (c=='$')
      c=39; // Keep DolDoc tags out of untrusted text.
    else if (c=='\n' || c=='\t')
    {
    }
    else if (c<32 || c>=127)
      c=' ';
    *d++=c;
  }
  *d=0;
  return res;
}

U8 *SouthpawCatField(U8 *out,U8 *label,U8 *val)
{
  U8 *safe;
  U8 *res;
  safe=SouthpawSafeText(val);
  res=MStrPrint("%s%s%s\n",out,label,safe);
  Free(out);
  Free(safe);
  return res;
}

CSouthpawPost *SouthpawNewPost()
{
  CSouthpawPost *p;
  p=CAlloc(sizeof(CSouthpawPost));
  p->id=StrNew("");
  p->author=StrNew("");
  p->kind=StrNew("");
  p->when=StrNew("");
  p->section=StrNew("");
  p->subject=StrNew("");
  p->body=StrNew("");
  return p;
}

U0 SouthpawLinkPost(CSouthpawPost **head,CSouthpawPost **tail,CSouthpawPost *p)
{
  p->next=NULL;
  if (*tail)
    (*tail)->next=p;
  else
    *head=p;
  *tail=p;
}

U0 SouthpawSetField(U8 **dst,U8 *st)
{
  Free(*dst);
  *dst=StrNew(SouthpawTrim(st));
}

U0 SouthpawPostsDel(CSouthpawPost *head)
{
  CSouthpawPost *p=head;
  CSouthpawPost *n;
  while (p)
  {
    n=p->next;
    Free(p->id);
    Free(p->author);
    Free(p->kind);
    Free(p->when);
    Free(p->section);
    Free(p->subject);
    Free(p->body);
    Free(p);
    p=n;
  }
}

U0 SouthpawAppendBody(U8 *bodybuf,I64 *bodylen,I64 bodymax,U8 *line)
{
  I64 ll,bl;
  ll=StrLen(line);
  bl=bodylen[0];
  if (bl+ll+2<bodymax)
  {
    MemCpy(bodybuf+bl,line,ll);
    bl+=ll;
    bodybuf[bl]='\n';
    bl++;
    bodybuf[bl]=0;
    bodylen[0]=bl;
  }
}

U0 SouthpawFinishPost(CSouthpawPost **head,CSouthpawPost **tail,
		      CSouthpawPost **cur,U8 **bodybuf,
		      I64 *count,I64 *agents)
{
  (*cur)->body=*bodybuf;
  *bodybuf=NULL;
  SouthpawLinkPost(head,tail,*cur);
  (*count)++;
  if (StrIMatch((*cur)->kind,"agent"))
    (*agents)++;
  *cur=NULL;
}

CSouthpawPost *SouthpawParseFile(U8 *filename,I64 *count,I64 *agents,U8 **channel)
{
  I64 size;
  I64 bodylen;
  I64 bodymax;
  Bool in_body=FALSE;
  U8 *buf;
  U8 *work;
  U8 *p;
  U8 *line;
  U8 *bodybuf;
  U8 c;
  CSouthpawPost *head;
  CSouthpawPost *tail;
  CSouthpawPost *cur;
  size=0;
  bodylen=0;
  bodybuf=NULL;
  head=NULL;
  tail=NULL;
  cur=NULL;

  *count=0;
  *agents=0;
  Free(*channel);
  *channel=StrNew("BBS");
  buf=FileRead(filename,&size);
  if (!buf)
    return NULL;
  work=MAlloc(size+1);
  MemCpy(work,buf,size);
  work[size]=0;
  Free(buf);
  bodymax=size+2;
  p=work;
  while (*p)
  {
    line=p;
    while (*p && *p!='\n' && *p!='\r')
      p++;
    if (*p)
    {
      c=*p;
      *p=0;
      p++;
      if (c=='\r' && *p=='\n')
        p++;
    }
    line=SouthpawTrim(line);
    if (cur && !StrCmp(line,"@end"))
    {
      SouthpawFinishPost(&head,&tail,&cur,&bodybuf,count,agents);
      in_body=FALSE;
    }
    else if (cur && in_body)
      SouthpawAppendBody(bodybuf,&bodylen,bodymax,line);
    else if (cur && !StrNCmp(line,"id:",3))
      SouthpawSetField(&cur->id,line+3);
    else if (cur && !StrNCmp(line,"from:",5))
      SouthpawSetField(&cur->author,line+5);
    else if (cur && !StrNCmp(line,"kind:",5))
      SouthpawSetField(&cur->kind,line+5);
    else if (cur && !StrNCmp(line,"time:",5))
      SouthpawSetField(&cur->when,line+5);
    else if (cur && !StrNCmp(line,"section:",8))
      SouthpawSetField(&cur->section,line+8);
    else if (cur && !StrNCmp(line,"subject:",8))
      SouthpawSetField(&cur->subject,line+8);
    else if (cur && !StrNCmp(line,"body:",5))
      in_body=TRUE;
    else if (!StrCmp(line,"@post"))
    {
      if (cur)
	SouthpawFinishPost(&head,&tail,&cur,&bodybuf,count,agents);
      cur=SouthpawNewPost();
      bodybuf=MAlloc(bodymax);
      bodybuf[0]=0;
      bodylen=0;
      in_body=FALSE;
    }
    else if (!StrNCmp(line,"@channel",8))
    {
      Free(*channel);
      *channel=StrNew(SouthpawTrim(line+8));
    }
    // Anything else is ignored.  It is never executed.
  }
  if (cur)
    SouthpawFinishPost(&head,&tail,&cur,&bodybuf,count,agents);
  if (bodybuf)
    Free(bodybuf);
  Free(work);
  return head;
}

U8 *SouthpawFixturePath()
{
  if (FileFind(SP_FIXTURE,,FUF_JUST_FILES))
    return SP_FIXTURE;
  if (FileFind("FIXTURES/SAMPLE.DIG",,FUF_JUST_FILES))
    return "FIXTURES/SAMPLE.DIG";
  if (FileFind("SAMPLE.DIG",,FUF_JUST_FILES))
    return "SAMPLE.DIG";
  return SP_FIXTURE;
}


#endif
