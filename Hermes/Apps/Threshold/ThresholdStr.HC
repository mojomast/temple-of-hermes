#define TH_NUM_DOORS	5
#define TH_NUM_MOTD	5
#define TH_LEFT		8
#define TH_FOOTER_H	16
#define TH_TITLE	"THE THRESHOLD"
#define TH_HOST		"Nous Girl"
#define TH_STATUS_FILE	"~/ThresholdStatus.TXT"

#define TH_ART_SPLASH	"Splash/toh-boot-splash.GR"
#define TH_ART_HEADER	"UI/pane-header.GR"
#define TH_ART_ICON	"Icons/64/nous-girl.GR"

U8 *th_door_name[TH_NUM_DOORS]={
  "Chat","Codex","BBS","Dojo","Offerings"};

U8 *th_door_desc[TH_NUM_DOORS]={
  "Hermes chat",
  "Codex of Nous",
  "Bulletin board",
  "Dojo practice",
  "Offerings"};

U8 *th_motd[TH_NUM_MOTD]={
  "The Threshold is open. Bring a question, leave with a door.",
  "One temple, two travelers: human and agent share this room.",
  "Small steps through big doors. The pinned apps are below.",
  "The archive remembers. The host only greets.",
  "Ask for what you need. The doors are named, not locked."};

U8 *ThresholdArtFile(U8 *rel)
{//Build <root>/Art/... from <root>/Apps/Threshold.
  U8 *d=StrNew(__DIR__),*res;
  StrLastRem(d,"/");
  StrLastRem(d,"/");
  res=MStrPrint("%s/Art/%s",d,rel);
  Free(d);
  return res;
}

U8 *ThresholdMotdText()
{//Pick today's MOTD without repeating a quote.
  CDateStruct ds;
  Date2Struct(&ds,Now+local_time_offset);
  return th_motd[(ds.day_of_mon+ds.mon)%TH_NUM_MOTD];
}

U8 *ThresholdPinnedText()
{//Comma separated pinned list for the status file.
  return StrNew("Chat,Codex,BBS,Dojo,Offerings");
}
