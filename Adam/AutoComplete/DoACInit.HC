#include "/Adam/AutoComplete/ACInit"

U0 DoACInit()
{
  Silent;       //no output to scrn
  ACInit("/*;!*/Bible.TXT*");
  Silent(OFF); //no output to scrn
  // Do not show the AutoComplete/System Keys guide at boot.  The dictionary
  // stays initialized; Alt-A toggles the guide later when the user wants it.
}

Spawn(&DoACInit);
