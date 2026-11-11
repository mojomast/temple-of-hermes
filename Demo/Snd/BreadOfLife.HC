// I tried...trust me it sounds better in church...so go to church!

U0 V1() {
  U8 *str_words = "I \0am \0the \0Bread \0of \0life. \0\n\0You \0who \0come \0to \0me \0shall \0not \0 \0hun\0-ger; \0\n\0and \0who \0be\0-lieve \0in \0me \0shall \0not \0thrist. \0\n\0No \0one \0can \0come \0to \0me \0un\0-less \0the \0 \0Fa\0-ther \0beck\0-ons. \0";
  U8 *str_notes  = "4qCqCqC3qAqA4q(EhEqEqEqFqFqFqFq(FqFqEq(EqEqEqEqEqAqAqAqGqGh.(FqFqEqEqEqCqEh.AqAqFq(FqFqFqFqEq.E";
  Play(str_notes, str_words);
}
U0 V2() {
  U8 *str_words = "The \0bread \0that \0 \0I \0will \0give\n\0 \0is \0my \0flesh \0for \0the \0life \0of \0the \0world,\n\0 \0 \0and \0if \0you \0eat \0 \0 \0of \0this \0bread\n\0 \0you \0shall \0 \0live \0for\0-ev\0-er \0you \0shall \0 \0live \0for\0-ev\0-er. \0";
  U8 *str_notes  = "4qCqCq(CqC3qAqA4q(EhEqEqEqFqFqFqFqFqFq(Eq(EqEqEqEqEq(Aq(AqAqGqGh.(FqFqEq(EqEqCqEh.AqAqFq(FqFqFqFqEq.E";
  Play(str_notes, str_words);
}
U0 V3() {
  U8 *str_words = "Un\0-less \0 \0 \0you \0 \0eat\0 \0\nof \0the \0flesh \0of \0the \0Son \0of \0 \0 \0Man \0 \0 \0 \0\nand \0 \0drink \0 \0of \0his \0blood \0\nand \0drink \0 \0 \0of \0his \0blood \0\nyou \0shall \0not \0have \0life \0with\0-in \0you. \0";
  U8 *str_notes  = "4qCq(Cq(CqC3q(AqA4q(EhEqEqEqFqFqFqFq(FqFq(Eq(EqEqEq(EqEq(AqAqAqGqGh.Fq(Fq(EqEqEqCqEh.AqAqFqFqFqFqFqEq.E";
  Play(str_notes, str_words);
}
U0 V4() {
  U8 *str_words = "I \0am \0the \0Res\0-ur\0-rec\0-tion\n\0 \0 \0I \0 \0 \0am \0the \0 \0life.\n\0 \0 \0If \0you \0be\0-lieve \0 \0 \0in \0 \0me \0 \0\ne\0-ven \0 \0though \0you \0die\n\0 \0you \0shall \0 \0live \0for\0-ev\0-er. \0";
  U8 *str_notes  = "4qCqCqC3qAqA4qEh(Eq(EqEq(Fq(FqFqFq(FqFq(Eq(EqEqEqEqEq(AqAq(AqGq(Gh.FqFq(EqEqEqCq(Eh.AqAq(FqFqFqFqFqEq.E";
  Play(str_notes, str_words);
}
U0 V5() {
  U8 *str_words = "Yes \0Lord \0 \0 \0I \0be\0-lieve\n\0 \0that \0 \0you \0 \0 \0are \0the \0 \0Christ \0 \0 \0 \0\nthe \0 \0Son \0 \0 \0of \0 \0God \0 \0who \0 \0 \0have \0 \0come \0in\0-to \0 \0 \0the \0 \0world. \0 \0";
  U8 *str_notes  = "4qCq(Cq(CqC3qAqA4q(EhEq(EqEq(Fq(FqFqFq(FqFq(Eq(EqEqEq(EqEq(Aq(AqAq(GqGh.(FqFq(Eq(EqEq(CqEh.AqAq(Fq(FqFq(FqFq(Eq.E";
  Play(str_notes, str_words);
}

U0 Refrain()
{
U8 *str_words = "And \0I \0will \0ra\0-ise \0you \0up,\0\n\0and \0I \0will \0ra\0-ise \0you \0up,\0\n\0and \0I \0will \0ra\0-ise \0you \0up \0 \0on \0the \0last \0 \0day.\n\0";
U8 *str_notes = "4eEqEqEh(AqBqB5h(CqC4qAqAqA5h(DqCqC4h(BqBqEqEqE5h(EqC4qA5q(DqC4qBqAh(AhGwA";
  "\n\n";
  Play(str_notes,str_words);
  "\n";
}

U0 Song()
{
  Fs->task_end_cb=&SndTaskEndCB;
  MusicSettingsRst;
  music.tempo= 3.0;
  music.stacatto_factor= 0.902;
#ifdef TINKEROS
  if (HaveOPL)
    SetInst(ECHODROP);
#endif
  DocMax;
  WinMax;
  DocClear;
  AutoComplete(0);
  V1;
  Refrain;
  V2;
  Refrain;
  V3;
  Refrain;
  V4;
  Refrain;
  V5;
  Refrain;
  Snd;
}

Song;
