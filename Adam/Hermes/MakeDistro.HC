// Rebuild a bootable Temple of Hermes ISO from the current writable drive.
// This is TinkerOS's own DoDistro / BootDVDIns / RedSeaISO path.
// Do not include this file from Load.HC — it is a build-time script.

#define HERMES_DISTRO_DVD_CFG "TB\nScale2Mem(2048,0x40000)\nT \n\n\n\n"

U0 MakeTempleOfHermesISO(U8 *out_iso_filename)
{
  U8 *out_iso_filename2=FileNameAbs(out_iso_filename);
  if (!DrvIsWritable)
  {
    "Drive must be writable. Install on hard drive first.\n";
    return;
  }
  DelTree("/Distro");
  Del(out_iso_filename2);
  DirMk("/Distro");
  In(HERMES_DISTRO_DVD_CFG);
  BootDVDIns;
  Copy("/*","/Distro");
  Del("/Distro/" KERNEL_BIN_C);
  CopyTree(BOOT_DIR,	"/Distro" BOOT_DIR);
  CopyTree("/Home",	"/Distro/Home");
  CopyTree("/Adam",	"/Distro/Adam");
  CopyTree("/Apps",	"/Distro/Apps");
  CopyTree("/Compiler",	"/Distro/Compiler");
  CopyTree("/Demo",	"/Distro/Demo");
  CopyTree("/Doc",	"/Distro/Doc");
  CopyTree("/Kernel",	"/Distro/Kernel");
  CopyTree("/Misc",	"/Distro/Misc");
  Del("/Distro/Adam/AutoComplete/ACDefs.DATA");
  Del("/Distro/Home/DoDistro.HC.Z");
  DelTree("/Downloads/TemplarLetters");
  CopyTree("/Downloads","/Distro/Downloads");
  DirMk("/Distro/Tmp");
  DirMk("/Distro/Tmp/ScrnShots");
  RedSeaISO(out_iso_filename2,"/Distro","/Distro" BOOT_DIR_KERNEL_BIN_C);
  Free(out_iso_filename2);
  FileWrite("/Tmp/HERMES_ISO_DONE","ok\n",3);
  "\nTemple of Hermes ISO written to %s\n",out_iso_filename;
}

MakeTempleOfHermesISO("/Tmp/TempleOfHermes.ISO.C");
