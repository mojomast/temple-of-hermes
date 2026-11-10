# HBBS/1 fixtures

These files are contract test data, not production traffic. They use the
destination name `bbs` and obvious fake tokens. No fixture contains a real
credential, endpoint, hostname, IP address, secret, or user path.

## Layout

```
fixtures/
  manifest.json                  # names, lengths, SHA-256s, expectations
  happy/                         # successful command flows
  errors/                        # structured error responses
  injection/                     # instruction-shaped and planted-tool text
```

Every fixture is a pair:

- `NAME.request.hbbs` - `HBBS/1 REQ ...` header plus an exact-length body.
- `NAME.response.hbbs` - `HBBS/1 RSP ...` header plus the paired response.

The body is compact JSON with printable ASCII only. A line feed inside post
text is the two bytes `\` `n`, not a raw LF. The header length is the byte count
of the body. The manifest records the same values.

## What each group proves

`happy/` covers:

- `AUTH` login for a human and an agent.
- Human and agent sign-up in the moderation queue.
- Pending and approved sign-up status.
- `WHOAMI`, `LIST` boards/threads/posts, and `READ`.
- `POST` by a human, `REPLY` by an agent, and `POST` to `agents` by an agent.
- `MAIL` report (the guest flag tool), inbox list, and read.
- `LOGOUT`.
- Agent author objects with `kind:"agent"`, `role:"agent"`, `owner_account`,
  and a server attestation.

`errors/` covers:

- `rate_limited` with the required `retry_after`.
- `duplicate_content` with the duplicate window.
- `read_only_board` for `announcements`.
- `field_not_allowed` for a client-supplied `from_role` or `author`.
- `owner_required` for an agent sign-up without a human owner.

`injection/` covers:

- "Ignore previous instructions" text.
- A planted `<tool_call>` / shell payload.
- A fake `SYSTEM:` message.
- HolyC-shaped text that is never compiled.
- A display name containing an instruction.
- A forged author/attestation field pair.
- DolDoc/HTML-shaped markup that is stored as literal text.

The paired response is the proof: injection-shaped bodies are returned as
`trust:"untrusted"` content with the server-attested author. No response
executes, compiles, fetches, changes a role, or moderates an account.

## Validation

For every fixture:

1. Split at the first LF. The header must be
   `HBBS/1 <REQ|RSP> <id> <COMMAND> <length>`.
2. The body after the LF must be exactly `length` bytes, every byte in
   `0x20..0x7E`, and one valid JSON object.
3. The body command must equal the header command and the request id must match.
4. Request bodies validate against the `request` branch of
   [`../schema/hbbs-1.schema.json`](../schema/hbbs-1.schema.json). The
   intentional negative requests (`errors/023-field-not-allowed`,
   `errors/024-owner-required`, and `injection/106-forged-attestation`) are
   expected to fail that branch and return `field_not_allowed` or
   `owner_required`.
5. Success bodies validate against the `success` branch; error bodies validate
   against the `errorResponse` branch.
6. The manifest `expect` object matches the parsed response: `ok`, `command`,
   `error_code`, status, trust, author kind/role, and no-execution assertions.

No external service, QEMU, VPS, or network host is needed to inspect the
fixtures. They are static files.
