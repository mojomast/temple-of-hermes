U0 CadAnimateTask(I64)
{
  while (TRUE) {
    if (cad_state==CAD_PLAY && cad_alive) {
      Sleep(cad_delay);
      if (cad_auto) CadAgentDir();
      CadStep();
      if (!cad_alive) CadEnd();
    } else
      Sleep(25);
  }
}

U0 CadSongTask(I64)
{
  Fs->task_end_cb=&SndTaskEndCB;
  MusicSettingsRst;
  while (TRUE)
    Play("4AB5C");
}

U0 CadLoadArt()
{
  cad_wall=NULL;
  cad_logo=NULL;
  cad_sp=NULL;
  if (FileFind("C:/Hermes/Art/Wallpaper/toh-temple-night.GR"))
    cad_wall=GRRead("C:/Hermes/Art/Wallpaper/toh-temple-night.GR",Fs);
  if (FileFind("C:/Hermes/Art/Icons/32/capy-caduceus.GR"))
    cad_logo=GRRead("C:/Hermes/Art/Icons/32/capy-caduceus.GR",Fs);
  if (FileFind("C:/Hermes/Art/Icons/32/southpaw.GR"))
    cad_sp=GRRead("C:/Hermes/Art/Icons/32/southpaw.GR",Fs);
}

U0 CadCleanUp()
{
  if (Fs->animate_task) {
    Kill(Fs->animate_task);
    Fs->animate_task=NULL;
  }
  if (Fs->song_task) {
    Kill(Fs->song_task);
    Fs->song_task=NULL;
  }
  Fs->draw_it=NULL;
  if (cad_wall) { DCDel(cad_wall); cad_wall=NULL; }
  if (cad_logo) { DCDel(cad_logo); cad_logo=NULL; }
  if (cad_sp) { DCDel(cad_sp); cad_sp=NULL; }
}
