//Place this file in /Home and change
//anything you want.

U0 UserStartUp()
{//Run each time a user a spawned
  DocTermNew;
  Type("::/Doc/Start.DD");
  LBts(&Fs->display_flags,DISPLAYf_SHOW);
  WinToTop;
  WinZBufUpdate;
  Dir;
}

U0 SrvStartUp()
{//Run each time a srv task is spawned.
  DocTermNew;
  LBts(&Fs->display_flags,DISPLAYf_SHOW);
  WinToTop;
  WinZBufUpdate;
}

U0 StartUpTasks()
{
  CTask *user1;
  // One terminal runs Once.  Keep it hidden so the Hermes launcher owns the
  // live-ISO screen; Ctrl-Alt-N still opens a visible user shell later.
  user1=User;
  XTalk(user1,"Cd;#include \"Once\";\n");
  LBtr(&user1->display_flags,DISPLAYf_SHOW);
  if (TaskValidate(user1))
    TaskDerivedValsUpdate(user1);
  "Boot Time:%7.3fs\n"
  ,tS;
}

StartUpTasks;

"\nTHE TEMPLE OF HERMES  (TinkerOS V%5.3f)\t%D %T\n\n"
,sys_os_version,sys_compile_time,sys_compile_time;
