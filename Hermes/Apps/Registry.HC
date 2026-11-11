#ifndef HERMES_APPS_REGISTRY_HC
#define HERMES_APPS_REGISTRY_HC

//The Hermes app registry.  The launcher and PersonalMenu both read this
//table.  "planned" entries are placeholders whose Run.HC files are not in
//this tree yet.  Icons are the existing files under ::/Hermes/Art/Icons/32
//(16 for the PersonalMenu sprites); no art is generated here.

#define HERMES_APPS_MAX 24

class CHermesApp
{
  U8 *id;
  U8 *title;
  U8 *icon;
  U8 *desc;
  U8 *run;
  Bool planned;
  I64 shortcut;
};

CHermesApp hermes_apps[HERMES_APPS_MAX];
I64 hermes_apps_num=0;

U0 HermesAppsRegistryAdd(U8 *id,U8 *title,U8 *icon,U8 *desc,U8 *run,Bool planned,I64 shortcut)
{
  CHermesApp *a;
  if (hermes_apps_num>=HERMES_APPS_MAX)
    return;
  a=&hermes_apps[hermes_apps_num++];
  a->id=id;
  a->title=title;
  a->icon=icon;
  a->desc=desc;
  a->run=run;
  a->planned=planned;
  a->shortcut=shortcut;
}

U0 HermesAppsRegistryInit()
{
  if (hermes_apps_num)
    return;
  HermesAppsRegistryAdd("home-temple",   "Temple",      "home-temple",
                        "The Temple of Hermes home screen.", NULL, FALSE,'T');
  HermesAppsRegistryAdd("hermes-chat",   "Hermes Chat", "hermes-chat",
                        "Talk with the Hermes agent over COM2.",
                        "::/Hermes/Apps/HermesChat/Run.HC", FALSE,'H');
  HermesAppsRegistryAdd("worldsim",      "WorldSim",    "worldsim",
                        "Agent world simulation.",
                        "::/Hermes/Apps/WorldSim/Run.HC", FALSE,'W');
  HermesAppsRegistryAdd("codex-of-nous", "Codex",       "codex-of-nous",
                        "Read the Codex of Nous from ::/Hermes/Lore.",
                        "::/Hermes/Apps/Codex/Run.HC", FALSE,'C');
  HermesAppsRegistryAdd("psyche",        "Psyche",      "psyche",
                        "Decentralized training monitor.",
                        "T:/Hermes/Apps/Psyche/Run.HC", FALSE,'P');
  HermesAppsRegistryAdd("capybara-pet",  "Capybara",    "capybara-pet",
                        "The Temple capybara.",
                        "::/Hermes/Apps/Capybara/Run.HC", FALSE,'B');
  HermesAppsRegistryAdd("messenger-run", "Messenger",   "messenger-run",
                        "Hermes messenger run.",
                        "::/Hermes/Apps/MessengerRun/Run.HC", FALSE,'M');
  HermesAppsRegistryAdd("hermes-bbs",    "BBS",         "modem-net",
                        "Temple of Hermes BBS (HBBS/1) over Hermes/Net.",
                        "::/Hermes/Apps/HermesBBS/Run.HC", FALSE,'S');
  HermesAppsRegistryAdd("threshold",     "Threshold",   "home-temple",
                        "The Threshold: the temple gate and cinematic splash.",
                        "::/Hermes/Apps/Threshold/Run.HC", FALSE,'R');
  HermesAppsRegistryAdd("dojo",          "Dojo",        "teknium",
                        "Teknium's Dojo: game-trainer challenges.",
                        "::/Hermes/Apps/Dojo/Run.HC", FALSE,'J');
  HermesAppsRegistryAdd("offerings",     "Offerings",   "don-piedro",
                        "Don Piedro's Offerings.",
                        "::/Hermes/Apps/Offerings/Run.HC", FALSE,'O');
  HermesAppsRegistryAdd("southpaw",      "Southpaw",    "southpaw",
                        "Southpaw: an announcer-fronted view of BBS highlights.",
                        "::/Hermes/Apps/Southpaw/Run.HC", FALSE,'U');
  HermesAppsRegistryAdd("modem-net",     "Modem / Net", "modem-net",
                        "COM2 serial modem status and loopback tools.",
                        "::/Hermes/Apps/Net/Run.HC", FALSE,'N');
  HermesAppsRegistryAdd("caduceus",      "Caduceus",    "capy-caduceus",
                        "Caduceus: guide the temple serpent.",
                        "::/Hermes/Apps/Caduceus/Run.HC", FALSE,'D');
  HermesAppsRegistryAdd("token-rain",    "Token Rain",  "nous-girl",
                        "Token Rain: Nous Girl at the Threshold.",
                        "::/Hermes/Apps/TokenRain/Run.HC", FALSE,'K');
  HermesAppsRegistryAdd("spoon",         "Spoon",       "don-piedro",
                        "Spoon: Don Piedro's catch arcade.",
                        "::/Hermes/Apps/Spoon/Run.HC", FALSE,'Q');
  HermesAppsRegistryAdd("dojo-duel",     "Dojo Duel",   "teknium",
                        "Dojo Duel: Teknium's challenge mode.",
                        "::/Hermes/Apps/DojoDuel/Run.HC", FALSE,'L');
  HermesAppsRegistryAdd("about",         "About",       "nous-girl",
                        "About the Temple of Hermes.",
                        "::/Hermes/Apps/About/Run.HC", FALSE,'A');
}

#endif
