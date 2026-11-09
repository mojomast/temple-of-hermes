// Refuse format / install / yes-no confirms while the agent is driving.

Bool HermesInputGate(U8 *what)
{
  U8 buf[80];
  if (!what) what="unknown";
  if (hermes_mode==HERMES_MODE_USER)
    return TRUE;
  if (!StrCmp(what,"YorN") && hermes_mode==HERMES_MODE_SHARED)
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
