// Guarded file I/O for the Hermes daemon.
//
// A daemon must never enter the debugger because a client sent a bad path.
// The kernel file helpers throw on an absent drive, a missing directory, or
// a read-only block device (Kernel/BlkDev/DskDrv.HC, DskDirContext.HC,
// DskBlk.HC).  Everything here validates first, uses the non-throwing
// Let2Drv/DrvIsWritable forms, and wraps the remaining kernel calls in
// try/catch.  Errors become one stable JSON body for an HRPL err reply.

#ifndef HERMES_FILEGUARD_HC
#define HERMES_FILEGUARD_HC

#define HERMES_FILE_PATH_MAX	1024

U8 HermesFileDriveOf(U8 *path)
{//Drive letter, ':' for ::, or 0 when the path is relative.
  if (!path || !*path)
    return 0;
  if (path[0]==':' && path[1]==':')
    return ':';
  if (path[1]==':')
  {
    if ('A'<=path[0]<='Z')
      return path[0];
    if ('a'<=path[0]<='z')
      return ToUpper(path[0]);
  }
  return 0;
}

U8 *HermesFileDriveStr(U8 drive)
{//MAlloc printable drive for an error body.
  U8 *s=MAlloc(2);
  if (drive)
    s[0]=drive;
  else
    s[0]='-';
  s[1]=0;
  return s;
}

Bool HermesFileDriveOk(U8 drive)
{//Never throws.  B: is created on demand.
  if (drive=='B')
    HermesStateMakeRam;
  if (!drive)
    return Let2Drv(0,FALSE)!=NULL;
  return Let2Drv(drive,FALSE)!=NULL;
}

Bool HermesFileDriveWritable(U8 drive)
{//Never throws.  Uses the kernel's read-only flag, not a trial write.
  Bool res=FALSE;
  if (drive=='B')
    HermesStateMakeRam;
  try
  {
    if (!drive)
      res=DrvIsWritable(0,FALSE)!=NULL;
    else
      res=DrvIsWritable(drive,FALSE)!=NULL;
  }
  catch
  {
    Fs->catch_except=TRUE;
    res=FALSE;
  }
  return res;
}

Bool HermesFileHasBadDotDot(U8 *path)
{
  U8 *p=path;
  if (!path)
    return TRUE;
  while (*p)
  {
    if (p[0]=='.' && p[1]=='.' &&
        (p[2]==0 || p[2]=='/') && (p==path || *(p-1)=='/'))
      return TRUE;
    p++;
  }
  return FALSE;
}

Bool HermesFilePathOk(U8 *path)
{
  if (!path || !*path)
    return FALSE;
  if (StrLen(path)>=HERMES_FILE_PATH_MAX)
    return FALSE;
  if (HermesFileHasBadDotDot(path))
    return FALSE;
  return TRUE;
}

U8 *HermesFileErrJSON(U8 *op,U8 *code,U8 *path,U8 drive)
{//Stable HRPL err body.  code is also mirrored in error.
  U8 *eo,*ec,*ep,*ed,*out;
  if (!op) op="file";
  if (!code) code="exception";
  if (!path) path="";
  eo=HermesEsc(op);
  ec=HermesEsc(code);
  ep=HermesEsc(path);
  ed=HermesFileDriveStr(drive);
  out=MStrPrint(
    "{\"ok\":0,\"error\":\"%s\",\"code\":\"%s\",\"op\":\"%s\","
    "\"drive\":\"%s\",\"path\":\"%s\"}",
    ec,ec,eo,ed,ep);
  Free(eo);
  Free(ec);
  Free(ep);
  Free(ed);
  return out;
}

Bool HermesFileFindSafe(U8 *path,CDirEntry *de,I64 flags,I64 *errch)
{
  Bool res=FALSE;
  if (errch) *errch=0;
  try
    res=FileFind(path,de,flags);
  catch
  {
    Fs->catch_except=TRUE;
    if (errch) *errch=Fs->except_ch;
    res=FALSE;
  }
  return res;
}

U8 *HermesFileReadSafe(U8 *path,I64 *size,I64 *errch)
{
  U8 *data=NULL;
  if (size) *size=0;
  if (errch) *errch=0;
  try
    data=FileRead(path,size);
  catch
  {
    Fs->catch_except=TRUE;
    if (errch) *errch=Fs->except_ch;
    data=NULL;
  }
  return data;
}

I64 HermesFileWriteSafe(U8 *path,U8 *data,I64 len,I64 *errch)
{
  I64 wrote=-1;
  if (errch) *errch=0;
  try
    wrote=FileWrite(path,data,len);
  catch
  {
    Fs->catch_except=TRUE;
    if (errch) *errch=Fs->except_ch;
    wrote=-1;
  }
  return wrote;
}

Bool HermesDirMkSafe(U8 *path,I64 *errch)
{
  Bool res=FALSE;
  if (errch) *errch=0;
  try
    res=DirMk(path);
  catch
  {
    Fs->catch_except=TRUE;
    if (errch) *errch=Fs->except_ch;
    res=FALSE;
  }
  return res;
}

CDoc *HermesDocReadSafe(U8 *path,I64 *errch)
{
  CDoc *doc=NULL;
  if (errch) *errch=0;
  try
    doc=DocRead(path);
  catch
  {
    Fs->catch_except=TRUE;
    if (errch) *errch=Fs->except_ch;
    doc=NULL;
  }
  return doc;
}

U8 *HermesFileParentPath(U8 *path)
{//MAlloc parent directory of path, or "" when there is no slash.
  I64 i,len;
  U8 *p;
  if (!path || !*path)
    return StrNew("");
  len=StrLen(path);
  i=len-1;
  while (i>=0 && path[i]!='/')
    i--;
  if (i<0)
    return StrNew("");
  if (!i)
    return StrNew("/");
  p=MAlloc(i+1);
  MemCpy(p,path,i);
  p[i]=0;
  if (i==2 && path[1]==':')
  {
    Free(p);
    return StrNew("C:/"); //caller only checks existence; letter is not used
  }
  return p;
}

Bool HermesFileIsRoot(U8 *dir)
{
  if (!dir || !*dir)
    return TRUE;
  if (!StrCmp(dir,"/"))
    return TRUE;
  if (StrLen(dir)==3 && dir[1]==':' && dir[2]=='/')
    return TRUE;
  if (StrLen(dir)==2 && dir[1]==':')
    return TRUE;
  return FALSE;
}

Bool HermesFileParentExists(U8 *path)
{
  U8 *par=HermesFileParentPath(path);
  Bool ok;
  I64 ech=0;
  if (HermesFileIsRoot(par))
  {
    Free(par);
    return TRUE;
  }
  ok=HermesFileFindSafe(par,NULL,FUF_JUST_DIRS,&ech);
  Free(par);
  return ok;
}

Bool HermesFileMkOneDir(U8 *dir,I64 *errch)
{
  Bool ok=FALSE;
  I64 ech=0;
  if (errch) *errch=0;
  if (HermesFileIsRoot(dir))
    return TRUE;
  if (HermesFileFindSafe(dir,NULL,FUF_JUST_DIRS,&ech))
    return TRUE;
  ok=HermesDirMkSafe(dir,&ech);
  if (errch) *errch=ech;
  if (ok)
    return TRUE;
  return HermesFileFindSafe(dir,NULL,FUF_JUST_DIRS,&ech);
}

Bool HermesFileMkParents(U8 *path)
{//Create missing parents one component at a time.  Writable check is the caller's.
  U8 *p;
  I64 i,len;
  Bool ok=TRUE;
  I64 ech=0;
  p=StrNew(path);
  len=StrLen(p);
  i=len-1;
  while (i>=0 && p[i]!='/')
    i--;
  if (i<=0)
  {
    Free(p);
    return TRUE;
  }
  p[i]=0;
  if (StrLen(p)==2 && p[1]==':')
  {
    Free(p);
    return TRUE;
  }
  len=StrLen(p);
  for (i=3; i<len; i++)
  {
    if (p[i]=='/')
    {
      p[i]=0;
      ok=HermesFileMkOneDir(p,&ech);
      p[i]='/';
      if (!ok)
        break;
    }
  }
  if (ok)
    ok=HermesFileMkOneDir(p,&ech);
  Free(p);
  return ok;
}

U8 *HermesFileWriteJSON(U8 *op,U8 *path,U8 *data,I64 len,Bool *ok)
{//Validate, then guarded write.  Returns success JSON or an error JSON.
  U8 drive,*ep;
  I64 wrote,ech=0;
  Bool parent_ok;
  if (ok) *ok=FALSE;
  if (!HermesFilePathOk(path))
    return HermesFileErrJSON(op,"bad_path",path,0);
  if (len<0 || len>HERMES_MAX_PAYLOAD)
    return HermesFileErrJSON(op,"too_large",path,0);
  drive=HermesFileDriveOf(path);
  if (!HermesFileDriveOk(drive))
    return HermesFileErrJSON(op,"bad_drive",path,drive);
  parent_ok=HermesFileParentExists(path);
  if (!HermesFileDriveWritable(drive))
  {
    if (!parent_ok)
      return HermesFileErrJSON(op,"missing_dir",path,drive);
    return HermesFileErrJSON(op,"read_only",path,drive);
  }
  if (!parent_ok && !HermesFileMkParents(path))
    return HermesFileErrJSON(op,"missing_dir",path,drive);
  wrote=HermesFileWriteSafe(path,data,len,&ech);
  if (ech || wrote<0)
    return HermesFileErrJSON(op,"write_failed",path,drive);
  if (ok) *ok=TRUE;
  ep=HermesEsc(path);
  return MStrPrint("{\"ok\":1,\"wrote\":%d,\"path\":\"%s\"}",wrote,ep);
}

U8 *HermesFileReadChecked(U8 *op,U8 *path,I64 *size,U8 **errjson,Bool *ok)
{//Caller frees the data and, on failure, the errjson body.
  U8 *data;
  U8 drive;
  I64 ech=0;
  if (size) *size=0;
  if (errjson) *errjson=NULL;
  if (ok) *ok=FALSE;
  if (!HermesFilePathOk(path))
  {
    if (errjson) *errjson=HermesFileErrJSON(op,"bad_path",path,0);
    return NULL;
  }
  drive=HermesFileDriveOf(path);
  if (!HermesFileDriveOk(drive))
  {
    if (errjson) *errjson=HermesFileErrJSON(op,"bad_drive",path,drive);
    return NULL;
  }
  if (!HermesFileFindSafe(path,NULL,0,&ech))
  {
    if (errjson) *errjson=HermesFileErrJSON(op,"missing_file",path,drive);
    return NULL;
  }
  data=HermesFileReadSafe(path,size,&ech);
  if (ech || !data)
  {
    if (errjson) *errjson=HermesFileErrJSON(op,"read_failed",path,drive);
    return NULL;
  }
  if (!size || *size<0 || *size>HERMES_MAX_PAYLOAD)
  {
    Free(data);
    if (errjson) *errjson=HermesFileErrJSON(op,"too_large",path,drive);
    return NULL;
  }
  if (ok) *ok=TRUE;
  return data;
}

#endif
