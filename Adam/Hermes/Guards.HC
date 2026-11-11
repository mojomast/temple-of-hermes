// Refuse format / install / yes-no confirms while the agent is driving.

Bool HermesGuardAllow(U8 *what)
{
  if (!what) what="unknown";
  if (hermes_mode==HERMES_MODE_USER)
    return TRUE;
  if (!StrCmp(what,"YorN") && hermes_mode==HERMES_MODE_SHARED)
    return TRUE;
  return FALSE;
}

Bool HermesInputGate(U8 *what)
{
  U8 buf[80];
  if (!what) what="unknown";
  if (HermesGuardAllow(what))
    return TRUE;
  StrPrint(buf,"%s",what);
  HermesEventPush("danger_blocked",buf);
  "\n[HERMES] blocked %s — switch mode to USER to allow.\n",what;
  return FALSE;
}

U0 HermesGuardsInstall()
{
  fp_input_gate=&HermesInputGate;
}

Bool HermesAllowDanger(U8 *what)
{
  return HermesInputGate(what);
}

U8 *HermesGuardJSON(U8 *what)
{
  U8 *ew,*out;
  Bool allow;
  if (!what || !*what) what="Fmt";
  allow=HermesGuardAllow(what);
  ew=HermesEsc(what);
  out=MStrPrint(
    "{\"mode\":\"%s\",\"safe_mode\":%d,\"what\":\"%s\",\"allow\":%d,"
    "\"input_gate\":%d,\"guard_installed\":%d,"
    "\"blocked\":[\"Fmt\",\"AreYouSure\",\"OSInstall\",\"BootHDIns\"],"
    "\"yorn_blocked\":%d}",
    HermesModeName,hermes_mode!=HERMES_MODE_USER,ew,allow,
    fp_input_gate!=NULL,fp_input_gate==&HermesInputGate,
    hermes_mode==HERMES_MODE_AGENT);
  Free(ew);
  return out;
}
