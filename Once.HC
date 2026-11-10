//Place this file in /Home and change
//anything you want.

//This file is executed by the
//first terminal window upon start-up.
//See $LK,"Once",A="FF:~/HomeSys.HC,Once"$ and $LK,"Home Files",A="FF:::/Doc/GuideLines.DD,/Home Files"$.

// THE TEMPLE OF HERMES: skip the live-CD install and tour prompts
// so an agent and a human can start working immediately. The
// installer is still available as OSInstall; if the agent is
// driving, fp_input_gate will refuse it.

U0 Tmp()
{
  OnceExe;
  "\n$$BG,PURPLE$$$$FG,YELLOW$$  THE TEMPLE OF HERMES  v0.1.0  $$FG$$$$BG$$\n\n";
  "A TempleOS / TinkerOS fork for an AI agent and a human\n";
  "sharing one machine. The Hermes daemon is already on COM1\n";
  "at 115200 8n1. Presence banner shows who is driving:\n";
  "USER, SHARED, or AGENT.\n\n";
  "Host protocol: HBEACON / HREQ / HRPL / HEVT  (see /Adam/Hermes)\n";
  "Install is not started automatically. To install later, run OSInstall;\n";
  "from USER mode only.\n\n";
}

U0 HermesStartApps()
{//Autostart the Hermes app launcher when its files are present.
  U8 *st;
  if (IsFile("::/Hermes/Apps/Launcher/Run.HC"))
    st=StrNew("::/Hermes/Apps/Launcher/Run.HC");
  else if (IsFile("T:/Hermes/Apps/Launcher/Run.HC"))
    st=StrNew("T:/Hermes/Apps/Launcher/Run.HC");
  else if (IsFile("C:/Hermes/Apps/Launcher/Run.HC"))
    st=StrNew("C:/Hermes/Apps/Launcher/Run.HC");
  else if (IsFile("~/Hermes/Apps/Launcher/Run.HC"))
    st=StrNew("~/Hermes/Apps/Launcher/Run.HC");
  else
    st=NULL;
  if (st)
  {
    ExeFile(st);
    Free(st);
  }
}

Tmp;
HermesStartApps;
