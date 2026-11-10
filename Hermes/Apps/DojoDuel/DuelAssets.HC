#ifndef DUEL_ASSETS_V2_HC_V5
#define DUEL_ASSETS_V2_HC_V5
#include "DuelGlobals.HC"
U8 *DuelAssetPath(U8 *rel)
{
  U8 *p=MStrPrint("%s/../../Art/%s",__DIR__,rel);
  if (FileFind(p)) return p;
  Free(p);
  return MStrPrint("C:/Hermes/Art/%s",rel);
}
U0 DuelLoadAssets()
{
  U8 *p;
  p=DuelAssetPath("UI/header-dojo.GR");
  duel_bar=GRRead(p); Free(p);
  p=DuelAssetPath("UI/header-dojo.GR");
  duel_plate=GRRead(p); Free(p);
  if (!duel_plate)
  {
    p=DuelAssetPath("UI/header-dojo-plate.GR");
    duel_plate=GRRead(p); Free(p);
  }
  p=DuelAssetPath("Icons/64/teknium.GR");
  duel_tek=GRRead(p); Free(p);
  if (!duel_tek)
  {
    p=DuelAssetPath("Icons/32/teknium.GR");
    duel_tek=GRRead(p); Free(p);
  }
}
U0 DuelFreeAssets()
{
  if (duel_plate) { DCDel(duel_plate); duel_plate=NULL; }
  if (duel_bar) { DCDel(duel_bar); duel_bar=NULL; }
  if (duel_tek) { DCDel(duel_tek); duel_tek=NULL; }
}
#endif
