#ifndef HERMES_NET_BUILD_HC
#define HERMES_NET_BUILD_HC

// THE TEMPLE OF HERMES - compile/load check for the actual Hermes/Net sources.
//
//   #include "B:/Hermes/Net/Build.HC";
//   HermesNetBuildCheck;
//
// Build.HC includes the real Load.HC (Glbls, Protocol, Modem) rather than
// re-typing any of the COM2 code.  A successful compile prints the banner and
// writes HERMES_NET_BUILD_OK on COM1 (initialising COM1 if the shell has not).

Cd(__DIR__);;
#include "Load"
Cd("..");;

U0 HermesNetBuildCheck()
{
  "HERMES/NET BUILD OK\n";
  "COM%d  baud=%d  line_max=%d  dest_max=%d\n",
        HERMES_NET_COM,HERMES_NET_BAUD,HERMES_NET_LINE_MAX,HERMES_NET_DEST_MAX;
  HermesNetStatus;
  if (!comm_ports[1].base)
  {
    CommInit;
    CommInit8n1(1,115200);
  }
  if (comm_ports[1].base)
    CommPutS(1,"HERMES_NET_BUILD_OK\n");
}

#endif
