// THE TEMPLE OF HERMES - guest COM2 networking.
//
//   #include "/Hermes/Net/Load"
//   if (HermesNetDial("hermes")) {
//     HermesNetSend("hello",5);
//     n=HermesNetRecv(buf,sizeof(buf));
//     HermesNetHangUp;
//   }
//
// COM2 is the modem link; COM1 remains the Hermes HRPC console.
Cd(__DIR__);;
#include "Glbls"
#include "Protocol"
#include "Modem"
Cd("..");;
