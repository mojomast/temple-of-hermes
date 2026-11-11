// Hermes home layout helpers. Returns allocated "OK ..."/"ERR code" strings.
// Paths: <drv>:/Home/<handle>/{JOURNAL.TXT,PROJECTS.TXT,Src/}.
#ifndef HERMES_HOME_HC
#define HERMES_HOME_HC
#define HERMES_HOME_LINE_MAX 200
U8 hermes_home_handle[33];
U8 hermes_home_drive='C';
Bool hermes_home_ready=FALSE;
U0 HMClean(U8 *d,U8 *s,I64 m)
{I64 p=0;if(!d||m<1)return;if(!s)s="";
 while(*s&&p<m-1){if(*s>=32&&*s!=127)d[p++]=*s;s++;}d[p]=0;}
Bool HMDrv(U8 d)
{Bool ok=FALSE;try{if(Let2Drv(d,FALSE))ok=DrvIsWritable(d,FALSE)!=NULL;}
 catch{Fs->catch_except=TRUE;ok=FALSE;}return ok;}
U8 *HMPath(U8 *leaf)
{if(!hermes_home_ready)return StrNew("");
 return MStrPrint("%c:/Home/%s/%s",hermes_home_drive,hermes_home_handle,leaf);}
U8 *HomeInit(U8 *handle=NULL,U8 drv='C')
{U8 *base,*dir,*src,*r,c;Bool ok=TRUE;I64 i,l;
 if(drv>='a'&&drv<='z')drv-=32;
 if(drv<'A'||drv>'Z')return StrNew("ERR bad_drive");
 if(!handle||!*handle)handle="hermes";
 l=StrLen(handle);
 if(l<1||l>32)return StrNew("ERR bad_handle");
 for(i=0;i<l;i++){c=handle[i];
  if(!((c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')||
       c=='.'||c=='-'||c=='_'))
   return StrNew("ERR bad_handle");}
 hermes_home_ready=FALSE;
 if(!HMDrv(drv))return MStrPrint("ERR drive_not_writable:%c",drv);
 base=MStrPrint("%c:/Home",drv);
 dir=MStrPrint("%s/%s",base,handle);
 src=MStrPrint("%s/Src",dir);
 try
 {
  DirMk(base);DirMk(dir);DirMk(src);
  if(!(FileFind(dir,NULL,FUF_JUST_DIRS)&&FileFind(src,NULL,FUF_JUST_DIRS)))ok=FALSE;
 }
 catch{Fs->catch_except=TRUE;ok=FALSE;}
 Free(src);
 if(!ok){Free(base);Free(dir);return StrNew("ERR mkdir_failed");}
 StrCpy(hermes_home_handle,handle);
 hermes_home_drive=drv;hermes_home_ready=TRUE;
 r=MStrPrint("OK %s",dir);Free(base);Free(dir);return r;}
U8 *HomeDir()
{if(!hermes_home_ready)return StrNew("ERR not_initialized");
 return MStrPrint("%c:/Home/%s",hermes_home_drive,hermes_home_handle);}
U8 *JournalAdd(U8 *text)
{U8 *path,*old,*out,line[HERMES_HOME_LINE_MAX+1];CDateStruct ds;I64 p,size=0,wrote=-1;
 if(!hermes_home_ready)return StrNew("ERR not_initialized");
 if(!text)text="";
 Date2Struct(&ds,Now+local_time_offset);
 StrPrint(line,"%04d-%02d-%02d %02d:%02d ",ds.year,ds.mon,ds.day_of_mon,ds.hour,ds.min);
 p=StrLen(line);
 while(*text&&p<HERMES_HOME_LINE_MAX){if(*text>=32&&*text!=127)line[p++]=*text;text++;}
 line[p]=0;
 path=HMPath("JOURNAL.TXT");old=NULL;
 try{if(FileFind(path))old=FileRead(path,&size);}
 catch{Fs->catch_except=TRUE;old=NULL;}
 if(!old)old=StrNew("");
 out=MStrPrint("%s%s\n",old,line);Free(old);
 try wrote=FileWrite(path,out,StrLen(out));
 catch{Fs->catch_except=TRUE;wrote=-1;}
 Free(out);Free(path);
 if(wrote<=0)return StrNew("ERR write_failed");
 return StrNew("OK journal_added");}
U8 *JournalTail(I64 n=5)
{U8 *path,*data,*r;I64 size=0,i,lines=0,start=0;
 if(!hermes_home_ready)return StrNew("ERR not_initialized");
 if(n<1)n=1;if(n>100)n=100;
 path=HMPath("JOURNAL.TXT");data=NULL;
 try{if(FileFind(path))data=FileRead(path,&size);}
 catch{Fs->catch_except=TRUE;data=NULL;}
 Free(path);
 if(!data)return StrNew("ERR no_journal");
 i=size-1;if(i>=0&&data[i]=='\n')i--;
 while(i>=0){if(data[i]=='\n'){lines++;if(lines>=n){start=i+1;break;}}i--;}
 r=StrNew(data+start);Free(data);return r;}
U8 *ProjectSet(U8 *current,U8 *next)
{U8 *path,*out,c[HERMES_HOME_LINE_MAX+1],n[HERMES_HOME_LINE_MAX+1];I64 wrote=-1;
 if(!hermes_home_ready)return StrNew("ERR not_initialized");
 HMClean(c,current,HERMES_HOME_LINE_MAX+1);
 HMClean(n,next,HERMES_HOME_LINE_MAX+1);
 out=MStrPrint("Current: %s\nNext: %s\n",c,n);
 path=HMPath("PROJECTS.TXT");
 try wrote=FileWrite(path,out,StrLen(out));
 catch{Fs->catch_except=TRUE;wrote=-1;}
 Free(out);Free(path);
 if(wrote<=0)return StrNew("ERR write_failed");
 return StrNew("OK projects_set");}
U8 *ProjectShow()
{U8 *path,*data;I64 size=0;
 if(!hermes_home_ready)return StrNew("ERR not_initialized");
 path=HMPath("PROJECTS.TXT");data=NULL;
 try{if(FileFind(path))data=FileRead(path,&size);}
 catch{Fs->catch_except=TRUE;data=NULL;}
 Free(path);
 if(!data)return StrNew("ERR no_projects");
 return data;}
#endif
