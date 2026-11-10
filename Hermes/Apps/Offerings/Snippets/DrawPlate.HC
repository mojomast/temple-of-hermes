// DrawPlate.HC - load one header plate and blit it.
// The plate is a 640x160 uncompressed .GR in the temple palette.
U0 DrawPlateDemo(U8 *path)
{
  CDC *plate,*dc;
  if (!path)
    path="T:/Hermes/Art/UI/header-offerings-plate.GR";
  plate=GRRead(path);
  if (!plate)
    return;
  dc=DCAlias;
  GrBlot(dc,0,0,plate);
  DCDel(plate);
  Refresh;
}
