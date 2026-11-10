Cd(__DIR__);;
#ifndef HERMES_NET_APP_LOAD_HC
#define HERMES_NET_APP_LOAD_HC

// THE TEMPLE OF HERMES - Modem / Net app.
//
// This includes the real Hermes/Net library from the sibling Net directory;
// there is no inline copy of the modem code here.  COM2 is the modem link and
// COM1 remains the Hermes HRPC console.

#help_index "Hermes/Apps"
#include "../../Net/Load.HC"
Cd(__DIR__);;
#include "Net"
Cd(__DIR__);;
#help_index ""

#endif
