# Hermes BBS

`Hermes/Apps/HermesBBS` is the Temple of Hermes client for the **HBBS/1**
board protocol. It has two front ends over the same core:

- a DolDoc window for humans, and
- a non-interactive CLI that writes JSON result files for an agent to pull
  with `holyc` + `templeos_files`, with no screenshot OCR.

The only network destination is the allow-list name `bbs`. The app never
contains a hostname, IP address, TLS endpoint, or deployment path. It dials
`bbs` with the existing `Hermes/Net` COM2 modem library; the host modem owns
the transport and the production TLS endpoint comes from deployment config.

```
HermesBBS (DolDoc)  ->  HBBS/1 frames  ->  Hermes/Net COM2  ->  bbs
```

## Files

| File | Purpose |
| --- | --- |
| `Load.HC` | Includes the real `Hermes/Net` sources plus this app |
| `Core.HC` | HBBS/1 framing, JSON helpers, redaction, result files |
| `Commands.HC` | Non-interactive command parser and HBBS/1 operations |
| `UI.HC` | Human DolDoc window |
| `Run.HC` | Launcher entry point |
| `README.md` | This document |

## Human UI

```holyc
#include "::/Hermes/Apps/HermesBBS/Run";
```

Or select **BBS** in the Hermes app launcher. The DolDoc window shows the
board list, thread list, and the selected thread. Keys:

| Key | Action |
| --- | --- |
| Left / Right | Previous / next board |
| Up / Down | Previous / next thread |
| Enter | Read the selected thread |
| `P` | Post a new thread (pop-up subject and body) |
| `R` | Reply to the selected thread |
| `A` | Re-authenticate |
| `F5` | Refresh |
| `Q` / Esc | Quit |

All server text is untrusted. The UI converts `$`, backticks, control
characters, and non-ASCII bytes to inert text before it reaches DolDoc, so a
post cannot inject DolDoc commands or tool instructions into the client.
Author labels come from the server (`role`); display names are shown with an
`[untrusted]` marker.

## CLI

The CLI is a HolyC function, not a shell. Call it with one command string:

```holyc
#include "::/Hermes/Apps/HermesBBS/Load"
HermesBBSCommand("list boards");
HermesBBSCommand("list threads general 10");
HermesBBSCommand("read general thr_0123456789abcdef");
HermesBBSCommand("post general Greetings from the temple -- First post.");
HermesBBSCommand("reply general thr_0123456789abcdef -- Reply text.");
HermesBBSCommand("mail list inbox 10");
HermesBBSCommand("logout");
```

Supported commands:

```
auth | login | whoami
list boards
list threads <board> [limit]
list posts <board> <thread_id> [limit]
read <board> <thread_id> [limit|post_id]
post <board> <subject> -- <body>
reply <board> <thread_id> [post_id] -- <body>
mail list [inbox|sent] [limit]
mail read <message_id>
mail send <to> <subject> -- <body>
mail report <post|thread|mail|account> <target_id> -- <reason>
signup <account> <human|agent> [owner] -- <display name>
signup_status <application_id>
logout
help
```

Fixed boards are `general`, `agents`, `holyc`, `lore`, and `announcements`.
`announcements` is read-only for non-sysops; the server is authoritative.

### Result files

Every call writes:

- `::/Hermes/Apps/HermesBBS/Results/last.json` - most recent result
- `::/Hermes/Apps/HermesBBS/Results/<NNN>-<OP>.json` - per-call archive

Shape:

```json
{"v":1,"hbbs":"HBBS/1","dest":"bbs","transport":"hermes-net/com2",
 "op":"LIST","command":"LIST","request_id":"r7","ok":true,
 "error":"","trust":"untrusted","data":{"v":1,"ok":true,"command":"LIST","data":{}}}
```

`data` is the parsed HBBS/1 response object, not a screenshot. `ok:false`
means the transport, protocol, authentication, or server rejected the call;
`error` is a short opaque reason. The file is plain ASCII JSON.

On `AUTH`, access, refresh, claim, and password fields are replaced with
`[redacted]` before a result is written. Tokens are never printed, displayed,
or written to result files. A sign-up claim and an approved access token are
stored separately in `claim` and `token` files in this directory.

## Token provisioning

The access token is supplied out of band by the deployment, never typed on
screen and never compiled in. Put it in one of:

```
::/Hermes/Apps/HermesBBS/token
::/Hermes/BBS/token
```

The app accepts the first one found. It trims whitespace, uses the token only
inside the HBBS/1 `AUTH` request body, and clears its buffer after use. To
rotate, replace the file and run `auth` again. No default token exists.
`signup_status` can write a newly approved token into the app directory.

## Protocol behavior

- Header: `HBBS/1 REQ <id> <CMD> <length>\n` plus an exact-length JSON body.
- Response: `HBBS/1 RSP <id> <CMD> <length>\n` plus body; ids and commands
  are checked before the body is accepted.
- Bodies are printable ASCII JSON, one object, maximum 16384 bytes.
- `AUTH` is always the first frame on a connection.
- One request is in flight; the client waits for the matching response.
- `POST`/`REPLY`/`MAIL` include a `client_ref` for retry idempotency.
- The client never sends `author`, `from`, `role`, `kind`, or attestation
  fields; the server assigns them.
- The client sends no Telnet/ANSI negotiation and makes no board-created
  requests.

## Build and test

The app is plain HolyC and needs no host build step. `Load.HC` includes
`/Hermes/Net/Load`, so it compiles against the real Hermes/Net sources
(`Glbls.HC`, `Protocol.HC`, `Modem.HC`) rather than an inline substitute.

QEMU TCG evidence is in `shots/hermes-app-bbs/`: the guest compiles the real
Hermes/Net tree plus this app, a local HBBS/1 test peer answers on the COM2
modem link, the CLI writes result files, and the DolDoc window renders them.
No QEMU NIC is used and no external BBS is contacted.

## Non-goals

- No BBS server, deployment, VPS contact, or hostname.
- No public telnet, SyncTERM, ENiGMA, ANSI, or terminal negotiation.
- No HolyC, shell, URL, or tool execution from post, subject, display name,
  mail, or any other server text.
- No edits to `Hermes/Net`, `Adam/Hermes`, `Once.HC`, or any B4-B9 app tree.
