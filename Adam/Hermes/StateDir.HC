// Writable state directory for Hermes apps on the live CD and on disk.
//
// The live ISO has no writable C:, so an app that calls DirMk("C:/Tmp")
// dies before it can draw.  This helper keeps the old paths on an installed
// disk and falls back to the B: RAM drive (created by KMain when initramfs
// is present) on a read-only boot drive.  Every DirMk here is inside try;
// callers still guard their own writes so an app launches even if no state
// can be saved.

#ifndef HERMES_STATEDIR_HC
#define HERMES_STATEDIR_HC

#define HERMES_STATE_RAM_BYTES	(8*1024*1024)

U0 HermesStateMakeRam()
{//Create B: if the initramfs RAM drive was not already mounted.
  CBlkDev *bd;
  if (Let2BlkDev('B',FALSE))
    return;
  try
  {
    bd=BlkDevNextFreeSlot('B',BDT_RAM);
    if (bd)
    {
      bd->max_blk=(HERMES_STATE_RAM_BYTES>>BLK_SIZE_BITS)-1;
      BlkDevAdd(bd,I64_MIN,FALSE,TRUE);
    }
  }
  catch
    Fs->catch_except=TRUE;
}

Bool HermesStateWritable()
{//TRUE when the boot/home drive accepts writes.  Never throws.
  return DrvIsWritable(':',FALSE)!=NULL;
}

U8 *HermesStateRamDir(U8 *app)
{//B:/Tmp/Hermes/<App>, then B:/Hermes/<App>, else empty string.
  U8 *dir,*probe;
  if (!app || !*app)
    app="Hermes";
  HermesStateMakeRam;
  if (!Let2BlkDev('B',FALSE))
    return StrNew("");
  dir=MStrPrint("B:/Tmp/Hermes/%s",app);
  try
  {
    DirMk("B:/Home");
    DirMk("B:/Tmp");
    DirMk("B:/Tmp/Hermes");
    DirMk(dir);
    probe=MStrPrint("%s/.probe",dir);
    FileWrite(probe,"ok",2);
    Free(probe);
    return dir;
  }
  catch
  {
    Fs->catch_except=TRUE;
    Free(dir);
  }
  dir=MStrPrint("B:/Hermes/%s",app);
  try
  {
    DirMk("B:/Hermes");
    DirMk(dir);
    probe=MStrPrint("%s/.probe",dir);
    FileWrite(probe,"ok",2);
    Free(probe);
    return dir;
  }
  catch
  {
    Fs->catch_except=TRUE;
    Free(dir);
    return StrNew("");
  }
}

U8 *HermesStateDir(U8 *app)
{//C:/Tmp on a writable boot drive, otherwise a B: RAM app folder.
  if (HermesStateWritable())
  {
    try
      DirMk("C:/Tmp");
    catch
      Fs->catch_except=TRUE;
    return StrNew("C:/Tmp");
  }
  return HermesStateRamDir(app);
}

U8 *HermesStateDirFor(U8 *app,U8 *pref)
{//Use an existing preferred dir when writable; otherwise use RAM.
  if (HermesStateWritable())
  {
    if (pref && *pref)
    {
      try
        DirMk(pref);
      catch
        Fs->catch_except=TRUE;
      return StrNew(pref);
    }
    return HermesStateDir(app);
  }
  return HermesStateRamDir(app);
}

U8 *HermesStateFile(U8 *app,U8 *leaf)
{//Full path for one app state file; empty string if none is writable.
  U8 *dir,*st;
  if (!leaf)
    leaf="state.txt";
  dir=HermesStateDir(app);
  if (!dir || !*dir)
  {
    if (dir)
      Free(dir);
    return StrNew("");
  }
  st=MStrPrint("%s/%s",dir,leaf);
  Free(dir);
  return st;
}

U8 *HermesStateFileFor(U8 *app,U8 *pref,U8 *leaf)
{//Full path under a preferred writable dir, or the RAM fallback.
  U8 *dir,*st;
  if (!leaf)
    leaf="state.txt";
  dir=HermesStateDirFor(app,pref);
  if (!dir || !*dir)
  {
    if (dir)
      Free(dir);
    return StrNew("");
  }
  st=MStrPrint("%s/%s",dir,leaf);
  Free(dir);
  return st;
}

#endif
