// THE TEMPLE OF HERMES - COM2 networking globals.
// Public-domain work, with credit to Terry A. Davis (TempleOS)
// and the TinkerOS authors (tinkeros/TinkerOS).

#define HERMES_NET_COM		2
#define HERMES_NET_BAUD		115200
#define HERMES_NET_LINE_MAX	256
#define HERMES_NET_DEST_MAX	64

// The host modem is off by default and allow-list only.  Nothing is dialed
// until HermesNetDial() is called with a destination the host allows.
public I64 hermes_net_open=FALSE;
public U8  hermes_net_dest[HERMES_NET_DEST_MAX];
public U8  hermes_net_last[HERMES_NET_LINE_MAX];

U0 HermesNetResetState()
{
  hermes_net_open=FALSE;
  hermes_net_dest[0]=0;
}

U8 *HermesNetStateName()
{
  if (hermes_net_open)
    return "connected";
  return "idle";
}
