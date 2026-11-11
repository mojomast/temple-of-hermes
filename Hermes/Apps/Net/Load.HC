Cd(__DIR__);;
#ifndef HERMES_NET_APP_LOAD_HC
#define HERMES_NET_APP_LOAD_HC

// THE TEMPLE OF HERMES - Modem / Net app.
//
// Include the real Hermes/Net library explicitly so a compressed .Z twin can
// never shadow the checked-in source.  COM2 is the modem link; COM1 remains
// the Hermes HRPC console.

#include "../../Net/Glbls.HC"
#include "../../Net/Protocol.HC"
#include "../../Net/Modem.HC"
Cd(__DIR__);;
#include "Net.HC"
Cd(__DIR__);;

#endif
