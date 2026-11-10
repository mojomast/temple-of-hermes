#ifndef HERMES_APPS_REGISTRY_HC
#define HERMES_APPS_REGISTRY_HC

//The Hermes app registry.  The launcher and PersonalMenu both read this
//table.  "planned" entries are placeholders only; their Run.HC files are
//not part of this change.  The icons are the existing files under
//::/Hermes/Art/Icons/32 (16 for the PersonalMenu sprites).

#define HERMES_APPS_MAX 16

class CHermesApp
{
  U8 *id;
  U8 *title;
  U8 *icon;
  U8 *desc;
  U8 *run;
  Bool planned;
};

CHermesApp hermes_apps[HERMES_APPS_MAX];
I64 hermes_apps_num=0;

U0 HermesAppsRegistryAdd(U8 *id,U8 *title,U8 *icon,U8 *desc,U8 *run,Bool planned)
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
}

U0 HermesAppsRegistryInit()
{
  if (hermes_apps_num)
    return;
  HermesAppsRegistryAdd("home-temple",   "Temple",      "home-temple",
                        "The Temple of Hermes home screen.", NULL, FALSE);
  HermesAppsRegistryAdd("hermes-chat",   "Hermes Chat", "hermes-chat",
                        "Talk with the Hermes agent over COM1.",
                        "::/Hermes/Apps/HermesChat/Run.HC", TRUE);
  HermesAppsRegistryAdd("worldsim",      "WorldSim",    "worldsim",
                        "Agent world simulation.",
                        "::/Hermes/Apps/WorldSim/Run.HC", TRUE);
  HermesAppsRegistryAdd("codex-of-nous", "Codex",       "codex-of-nous",
                        "Notes from the Codex of Nous.",
                        "::/Hermes/Apps/Codex/Run.HC", TRUE);
  HermesAppsRegistryAdd("psyche",        "Psyche",      "psyche",
                        "Decentralized training monitor.",
                        "::/Hermes/Apps/Psyche/Run.HC", TRUE);
  HermesAppsRegistryAdd("capybara-pet",  "Capybara",    "capybara-pet",
                        "The Temple capybara.",
                        "::/Hermes/Apps/Capybara/Run.HC", TRUE);
  HermesAppsRegistryAdd("messenger-run", "Messenger",   "messenger-run",
                        "Hermes messenger run.",
                        "::/Hermes/Apps/MessengerRun/Run.HC", TRUE);
  HermesAppsRegistryAdd("modem-net",     "Modem / Net", "modem-net",
                        "Serial and network tools.",
                        "::/Hermes/Apps/Net/Run.HC", TRUE);
  HermesAppsRegistryAdd("nous-girl",     "About",       "nous-girl",
                        "About the Temple of Hermes.", NULL, FALSE);
}

#endif
