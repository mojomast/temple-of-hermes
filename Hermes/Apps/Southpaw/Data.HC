// Southpaw data definitions.  No side effects in this file.

#ifndef SOUTHP_DATA
#define SOUTHP_DATA

#define SP_NAME		"Southpaw"
#define SP_PLATE	"../../Art/UI/header-southpaw-plate.GR"
#define SP_ICON16	"../../Art/Icons/16/southpaw.GR"
#define SP_ICON32	"../../Art/Icons/32/southpaw.GR"
#define SP_ICON64	"../../Art/Icons/64/southpaw.GR"
#define SP_FIXTURE	"Fixtures/sample.digest"
#define SP_RESULT	"SOUTHP.TXT"

class CSouthpawPost
{
  CSouthpawPost *next;
  U8 *id,*author,*kind,*when,*section,*subject,*body;
};


#endif
