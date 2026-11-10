#ifndef HERMES_OFFERINGS_DATA_HC
#define HERMES_OFFERINGS_DATA_HC

#define OFFER_MAX 12
#define OFFER_WALL 0
#define OFFER_PAL  1
#define OFFER_SNIP 2

class COfferItem
{
  U8 *id;
  U8 *title;
  U8 *blurb;
  U8 *src;
  U8 *dest;
  U8 *kind;
  I64 price;
  I64 cat;
  Bool is_new;
  Bool installed;
};

COfferItem offer_items[OFFER_MAX];
I64 offer_count=0;
Bool offer_inited=FALSE;

U0 OfferAdd(U8 *id,U8 *title,U8 *blurb,U8 *src,U8 *dest,U8 *kind,
  I64 price,I64 cat,Bool is_new)
{
  COfferItem *it;
  if (offer_count>=OFFER_MAX)
    return;
  it=&offer_items[offer_count++];
  it->id=id;
  it->title=title;
  it->blurb=blurb;
  it->src=src;
  it->dest=dest;
  it->kind=kind;
  it->price=price;
  it->cat=cat;
  it->is_new=is_new;
  it->installed=FALSE;
}

U0 OfferingsInit()
{
  if (offer_inited)
    return;
  offer_inited=TRUE;
  OfferAdd("wall-nous-girl","Nous Girl",
    "The recommended night portrait. NEW in the temple.",
    "Art/Wallpaper/toh-nous-girl.GR","Wallpapers/toh-nous-girl.GR",
    "wallpaper",3,OFFER_WALL,TRUE);
  OfferAdd("wall-temple-night","Night",
    "The old courtyard after dark.",
    "Art/Wallpaper/toh-temple-night.GR","Wallpapers/toh-temple-night.GR",
    "wallpaper",2,OFFER_WALL,FALSE);
  OfferAdd("wall-hero","Hero",
    "A wide hall for the messenger.",
    "Art/Wallpaper/toh-hero.GR","Wallpapers/toh-hero.GR",
    "wallpaper",4,OFFER_WALL,FALSE);
  OfferAdd("wall-messenger-flight","Messenger",
    "Wings over the temple road.",
    "Art/Wallpaper/toh-messenger-flight.GR","Wallpapers/toh-messenger-flight.GR",
    "wallpaper",3,OFFER_WALL,FALSE);
  OfferAdd("wall-psyche","Psyche",
    "A neural flower for the quiet hours.",
    "Art/Wallpaper/toh-psyche.GR","Wallpapers/toh-psyche.GR",
    "wallpaper",3,OFFER_WALL,FALSE);
  OfferAdd("wall-worldsim","WorldSim",
    "A globe with little agents in orbit.",
    "Art/Wallpaper/toh-worldsim.GR","Wallpapers/toh-worldsim.GR",
    "wallpaper",3,OFFER_WALL,FALSE);
  OfferAdd("wall-logo","Logo",
    "The house mark, plain and proud.",
    "Art/Wallpaper/toh-logo.GR","Wallpapers/toh-logo.GR",
    "wallpaper",1,OFFER_WALL,FALSE);
  OfferAdd("pal-temple16","Temple 16",
    "The canonical sixteen-color palette card.",
    "Apps/Offerings/Palettes/Temple16.PAL","Palettes/Temple16.PAL",
    "palette",1,OFFER_PAL,FALSE);
  OfferAdd("pal-splash16","Splash 16",
    "The boot-splash sixteen-color swatches.",
    "Apps/Offerings/Palettes/Splash16.PAL","Palettes/Splash16.PAL",
    "palette",2,OFFER_PAL,FALSE);
  OfferAdd("snip-drawplate","Draw Plate",
    "Load a .GR header plate and blit it.",
    "Apps/Offerings/Snippets/DrawPlate.HC","Snippets/DrawPlate.HC",
    "snippet",2,OFFER_SNIP,TRUE);
  OfferAdd("snip-windowloop","Window Loop",
    "Spawn a task, take keys, leave on Esc.",
    "Apps/Offerings/Snippets/WindowLoop.HC","Snippets/WindowLoop.HC",
    "snippet",2,OFFER_SNIP,FALSE);
  OfferAdd("snip-agentfile","Agent File",
    "Write a small catalog for an agent.",
    "Apps/Offerings/Snippets/AgentResult.HC","Snippets/AgentResult.HC",
    "snippet",3,OFFER_SNIP,FALSE);
}

COfferItem *OfferFindItem(U8 *id)
{
  I64 i;
  OfferingsInit;
  if (!id)
    return NULL;
  for (i=0;i<offer_count;i++)
    if (!StrCmp(id,offer_items[i].id))
      return &offer_items[i];
  return NULL;
}

U8 *OfferCatName(I64 cat)
{
  if (cat==OFFER_WALL)
    return "Wallpaper";
  if (cat==OFFER_PAL)
    return "Palette";
  return "Snippet";
}



#define OFFER_MODE_SHOP 0
#define OFFER_MODE_WALL 1
#define OFFER_MODE_SNIP 2
#define OFFER_MODE_PAL  3

class COfferUI
{
  CDC *plate;
  CDC *piedro;
  CDC *wall;
  I64 selected;
  I64 mode;
  I64 spoons;
  U8 *status;
  U8 *snippet_text;
  U8 *snippet_name;
};

#endif
