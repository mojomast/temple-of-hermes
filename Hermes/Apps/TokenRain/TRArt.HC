CDC *TRLoadGR(U8 *rel,U8 *abs)
{
  U8 *b=FileRead(rel);
  CDC *res;
  if (!b)
    b=FileRead(abs);
  if (!b)
    return NULL;
  res=DCLoad(b);
  Free(b);
  return res;
}

U0 TRLoadArt()
{
  tr_hdr=TRLoadGR("../../Art/UI/header-threshold.GR","C:/Hermes/Art/UI/header-threshold.GR");
  if (!tr_hdr)
    tr_hdr=TRLoadGR("../../Art/UI/pane-header.GR","C:/Hermes/Art/UI/pane-header.GR");
  tr_plate=TRLoadGR("../../Art/UI/header-threshold-plate.GR","C:/Hermes/Art/UI/header-threshold-plate.GR");
  tr_gr=TRLoadGR("../../Art/Icons/64/nous-girl.GR","C:/Hermes/Art/Icons/64/nous-girl.GR");
  tr_icon32=TRLoadGR("../../Art/Icons/32/nous-girl.GR","C:/Hermes/Art/Icons/32/nous-girl.GR");
  tr_icon16=TRLoadGR("../../Art/Icons/16/nous-girl.GR","C:/Hermes/Art/Icons/16/nous-girl.GR");
}

U0 TRFreeArt()
{
  if (tr_hdr)
    DCDel(tr_hdr);
  if (tr_gr)
    DCDel(tr_gr);
  if (tr_plate)
    DCDel(tr_plate);
  if (tr_icon32)
    DCDel(tr_icon32);
  if (tr_icon16)
    DCDel(tr_icon16);
  tr_hdr=tr_gr=tr_plate=tr_icon32=tr_icon16=NULL;
}
