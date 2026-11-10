// Install.HC hook for the CODEX OF NOUS.
// Run once from a shell:  #include "/Hermes/Lore/Install";
//
// It copies the codex into ~/Lore and prints the one-line load hook.
// It deliberately does NOT edit Once.HC.

Cd(__DIR__);;

U8 *lore_files[]=
{
  "Glbls.HC",
  "Codex.HC",
  "MOTD.HC",
  "Oracle.HC",
  "Eggs.HC",
  "Load.HC",
  "Install.HC",
  "README.TXT"
};

I64 i,n=sizeof(lore_files)/sizeof(U8 *);
U8 *src,*dst;

if (!FileFind("~/Lore",,FUF_JUST_DIRS))
  DirMk("~/Lore");

for (i=0; i<n; i++)
{
  src=MStrPrint("%s/%s",__DIR__,lore_files[i]);
  dst=MStrPrint("~/Lore/%s",lore_files[i]);
  if (FileFind(src))
    Copy(src,dst);
  Free(src);
  Free(dst);
}

"\n$$YELLOW$$CODEX OF NOUS$$FG$$ installed in ~/Lore\n\n";
"Load it now:    #include \"~/Lore/Load\";\n";
"Every boot:     add that same line inside StartUpTasks in\n";
"                ~/HomeSys.HC, or at the end of ~/Once.HC.\n\n";
"$$LTGRAY$$This hook did not modify Once.HC.$$FG$$\n";
