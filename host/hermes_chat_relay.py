#!/usr/bin/env python3
"""Host side of the Temple of Hermes chat link on COM2.

The guest ``Hermes/Net`` library dials the allow-listed destination
``hermes`` with ordinary Hayes commands.  This module is the matching modem:
it is off by default, denies every destination not named in an explicit
allow-list, and never opens a socket or serial port on its own.

Once a chat is connected, each ``AT+SEND`` payload is one chat frame:

    guest -> host   HCHAT1 <text>
    host -> guest   HCHAT1 <text>
    host -> guest   HCHAT1-ERR <reason>

Payload bytes are not logged unless ``log_messages=True`` is passed
explicitly.  Tests use the in-memory API and a scripted responder.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Callable, Iterable, Protocol

__all__ = [
    "CRLF",
    "DEFAULT_BAUD",
    "ERR_PREFIX",
    "HermesChatRelay",
    "HermesResponder",
    "MAX_RECV",
    "MAX_SEND",
    "PREFIX",
    "RelayError",
    "ScriptedResponder",
    "encode_frame",
    "main",
    "run_socket",
    "run_stdio",
]

CRLF = b"\r\n"
DEFAULT_BAUD = 115200
MAX_SEND = 1 << 20
MAX_RECV = 1 << 16
PREFIX = "HCHAT1 "
ERR_PREFIX = "HCHAT1-ERR "


class RelayError(RuntimeError):
    """Raised for an unusable relay configuration or transport."""


class ChatResponder(Protocol):
    def reply(self, text: str) -> str:
        ...


class HermesResponder:
    """Small deterministic stand-in for the Hermes agent.

    It keeps the sandbox run offline and reproducible.  A real deployment
    can pass any object with a ``reply(text) -> str`` method.
    """

    def __init__(self, name: str = "hermes") -> None:
        self.name = name

    def reply(self, text: str) -> str:
        body = text.strip()
        low = body.lower()
        if not body:
            return "Say something and I will answer."
        if low in ("ping", "/ping"):
            return "pong"
        if low in ("help", "/help"):
            return "Hermes Chat: type a message, /connect retries, /quit hangs up."
        if low in ("hi", "hello", "hey"):
            return "Hello from Hermes."
        return f"Hermes heard: {body}"


class ScriptedResponder:
    """Test double that returns queued replies, then a fallback."""

    def __init__(self, replies: Iterable[str] = (), fallback: str = "ok") -> None:
        self.replies = list(replies)
        self.fallback = fallback
        self.seen: list[str] = []

    def reply(self, text: str) -> str:
        self.seen.append(text)
        if self.replies:
            return self.replies.pop(0)
        return self.fallback


class CallableResponder:
    def __init__(self, fn: Callable[[str], str]) -> None:
        self.fn = fn

    def reply(self, text: str) -> str:
        return self.fn(text)


def encode_frame(text: str) -> bytes:
    """Encode one guest request frame."""
    return (PREFIX + text.replace("\r", " ").replace("\n", " ")).encode(
        "utf-8", "replace"
    )


class HermesChatRelay:
    """Hayes modem plus the ``hermes`` chat endpoint.

    Parameters
    ----------
    enabled:
        Networking is off by default.  While false, ``ATD``, ``AT+SEND`` and
        ``AT+RECV`` answer ``ERROR``.
    allow_list:
        Exact, case-insensitive destination names.  Empty means deny all.
    responder:
        Object with ``reply(text) -> str``.  Defaults to
        :class:`HermesResponder`.
    log_path / logger:
        Optional command log.  Message payloads are omitted unless
        ``log_messages`` is true.
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        allow_list: Iterable[str] = (),
        responder: ChatResponder | None = None,
        log_path: str | Path | None = None,
        logger: Callable[[str], None] | None = None,
        log_messages: bool = False,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.enabled = bool(enabled)
        self.allow_list = tuple(
            str(d).strip().lower() for d in allow_list if str(d).strip()
        )
        self.responder: ChatResponder = responder or HermesResponder()
        self.log_path = Path(log_path) if log_path is not None else None
        self._logger = logger
        self.log_messages = bool(log_messages)
        self._clock = clock
        self.connected_to: str | None = None
        self.echo = False
        self._buf = bytearray()
        self._out = bytearray()
        self._pending_send: int | None = None
        self._pending_discard: int | None = None
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def connected(self) -> bool:
        return self.connected_to is not None

    @property
    def queued_bytes(self) -> int:
        return len(self._out)

    def is_allowed(self, destination: str) -> bool:
        return destination.strip().lower() in self.allow_list

    def _log(self, event: str, detail: str = "") -> None:
        line = f"{self._clock():.3f} {event}"
        if detail:
            line += f" {detail}"
        if self._logger is not None:
            try:
                self._logger(line)
            except Exception:
                pass
        if self.log_path is not None:
            try:
                with self.log_path.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError:
                pass

    def reset(self) -> None:
        self._hangup()
        self._buf.clear()
        self._out.clear()
        self._pending_send = None
        self._pending_discard = None

    def _hangup(self) -> None:
        if self.connected_to is not None:
            self._log("HANGUP", self.connected_to)
        self.connected_to = None

    def _dial(self, destination: str) -> bytes:
        destination = destination.strip()
        if not destination:
            return b"ERROR" + CRLF
        key = destination.lower()
        if not self.enabled:
            self._log("DENY", f"disabled dest={key}")
            return b"ERROR" + CRLF
        if not self.is_allowed(key):
            self._log("DENY", f"allow-list dest={key}")
            return b"ERROR" + CRLF
        self._hangup()
        self.connected_to = key
        self._log("DIAL", f"dest={key} result=connect")
        return b"CONNECT " + key.encode("ascii", "replace") + CRLF

    def _queue_frame(self, text: str) -> None:
        text = text.replace("\r", " ").replace("\n", " ")
        frame = (PREFIX + text).encode("utf-8", "replace")
        if len(frame) > MAX_RECV:
            frame = frame[:MAX_RECV]
        self._out.extend(frame)

    def _queue_error(self, reason: str) -> None:
        reason = reason.replace("\r", " ").replace("\n", " ")
        self._out.extend((ERR_PREFIX + reason).encode("utf-8", "replace"))

    def _accept_payload(self, payload: bytes) -> bytes:
        try:
            line = payload.decode("utf-8", "replace").rstrip("\r\n")
        except Exception:
            self._queue_error("bad encoding")
            return b"OK 0" + CRLF
        if not line.startswith(PREFIX):
            self._log("CHAT", "result=bad-frame")
            self._queue_error("bad frame")
            return f"OK {len(payload)}".encode("ascii") + CRLF
        body = line[len(PREFIX) :]
        if self.log_messages:
            self._log("CHAT", f"text={body!r}")
        else:
            self._log("CHAT", f"bytes={len(payload)}")
        try:
            reply = str(self.responder.reply(body))
        except Exception as exc:
            self._log("CHAT", f"result=responder-error type={type(exc).__name__}")
            self._queue_error("responder failed")
            return f"OK {len(payload)}".encode("ascii") + CRLF
        self._queue_frame(reply)
        return f"OK {len(payload)}".encode("ascii") + CRLF

    def _recv(self, maximum: int) -> bytes:
        if not self.enabled or not self.connected:
            self._log("DENY", "recv not-connected-or-disabled")
            return b"ERROR" + CRLF
        if maximum <= 0:
            return b"DATA 0" + CRLF
        maximum = min(maximum, MAX_RECV)
        data = bytes(self._out[:maximum])
        del self._out[: len(data)]
        self._log("RECV", f"bytes={len(data)}")
        return f"DATA {len(data)}".encode("ascii") + CRLF + data

    def _status(self) -> bytes:
        state = self.connected_to or "-"
        return (
            f"STATUS enabled={int(self.enabled)} connected={int(self.connected)} "
            f"dest={state} allow={len(self.allow_list)} queued={len(self._out)}"
        ).encode("ascii") + CRLF

    def _handle_line(self, raw: bytes) -> bytes:
        text = raw.decode("ascii", "replace").strip()
        if not text:
            return b""
        self._log("CMD", text if len(text) <= 96 else text[:93] + "...")
        upper = text.upper()

        if upper == "AT":
            return b"OK" + CRLF
        if upper in ("ATZ", "AT&F"):
            self.reset()
            return b"OK" + CRLF
        if upper == "ATI":
            return b"Temple of Hermes chat relay" + CRLF
        if upper in ("ATE0", "ATE1"):
            self.echo = upper == "ATE1"
            return b"OK" + CRLF
        if upper == "ATH":
            self._hangup()
            return b"OK" + CRLF
        if upper.startswith("AT+STATUS"):
            return self._status()
        if upper.startswith("ATD"):
            return self._dial(self._dial_argument(text))
        if upper.startswith("AT+SEND"):
            return self._begin_send(text[7:])
        if upper.startswith("AT+RECV"):
            return self._recv(self._number_argument(text[7:]))
        self._log("ERROR", "unknown command")
        return b"ERROR" + CRLF

    @staticmethod
    def _dial_argument(text: str) -> str:
        rest = text[3:].strip()
        if rest[:1] in ("T", "P", "t", "p"):
            nxt = rest[1:2]
            if nxt == "" or nxt.isspace() or nxt.isdigit() or nxt in "+-()":
                rest = rest[1:].strip()
        return rest

    @staticmethod
    def _number_argument(text: str) -> int:
        rest = text.strip()
        if rest.startswith("="):
            rest = rest[1:]
        try:
            return int(rest.split()[0])
        except (ValueError, IndexError):
            return -1

    def _begin_send(self, text: str) -> bytes:
        length = self._number_argument(text)
        if length < 0 or length > MAX_SEND:
            return b"ERROR" + CRLF
        if not self.enabled or not self.connected:
            self._log("DENY", "send not-connected-or-disabled")
            self._pending_discard = length
            return b"ERROR" + CRLF
        if length == 0:
            return self._accept_payload(b"")
        self._pending_send = length
        return b""

    def feed(self, data: bytes) -> bytes:
        """Consume guest bytes and return bytes to write back on COM2."""
        if not data:
            return b""
        self._buf.extend(data)
        out = bytearray()
        while True:
            if self._pending_discard is not None:
                need = self._pending_discard
                if len(self._buf) < need:
                    break
                del self._buf[:need]
                self._pending_discard = None
                continue
            if self._pending_send is not None:
                need = self._pending_send
                if len(self._buf) < need:
                    break
                payload = bytes(self._buf[:need])
                del self._buf[:need]
                self._pending_send = None
                out += self._accept_payload(payload)
                continue
            cr = self._buf.find(b"\r")
            lf = self._buf.find(b"\n")
            if cr < 0 and lf < 0:
                break
            if cr < 0:
                idx = lf
            elif lf < 0:
                idx = cr
            else:
                idx = min(cr, lf)
            line = bytes(self._buf[:idx])
            del self._buf[: idx + 1]
            out += self._handle_line(line)
        return bytes(out)

    def command(self, text: str) -> str:
        """Run one command and return the ASCII response, stripped."""
        if not text.endswith("\r") and not text.endswith("\n"):
            text += "\r"
        return self.feed(text.encode("ascii", "replace")).decode(
            "ascii", "replace"
        ).strip()


def _run_stdio(relay: HermesChatRelay) -> int:
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    while True:
        chunk = stdin.read(4096)
        if not chunk:
            return 0
        reply = relay.feed(chunk)
        if reply:
            stdout.write(reply)
            stdout.flush()


def run_socket(relay: HermesChatRelay, path: str | Path, timeout: float = 60.0) -> int:
    """Connect to a QEMU COM2 unix socket and serve it until EOF."""
    import socket

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    deadline = time.time() + timeout
    last: Exception | None = None
    while time.time() < deadline:
        try:
            sock.connect(str(path))
            break
        except OSError as exc:
            last = exc
            time.sleep(0.1)
    else:
        sock.close()
        raise RelayError(f"COM2 socket connect failed: {path}: {last}")
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                return 0
            reply = relay.feed(chunk)
            if reply:
                sock.sendall(reply)
    finally:
        sock.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Temple of Hermes COM2 chat relay (off by default, allow-list only)"
    )
    parser.add_argument("--enable", action="store_true", help="enable dialing")
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="DEST",
        help="add DEST to the allow-list (repeatable; default deny-all)",
    )
    parser.add_argument("--connect", type=Path, default=None, help="QEMU COM2 unix socket")
    parser.add_argument("--stdio", action="store_true", help="bridge AT bytes on stdin/stdout")
    parser.add_argument("--log", type=Path, default=None, help="append a command log")
    parser.add_argument(
        "--log-messages",
        action="store_true",
        help="include chat text in the log (off by default)",
    )
    parser.add_argument("--demo", action="store_true", help="run an in-memory transcript")
    args = parser.parse_args(argv)

    allow = args.allow or (["hermes"] if args.demo else [])
    relay = HermesChatRelay(
        enabled=args.enable or args.demo,
        allow_list=allow,
        log_path=args.log,
        log_messages=args.log_messages,
    )

    if args.demo:
        for step in (
            b"AT\r",
            b"ATZ\r",
            b"ATD hermes\r",
            b"AT+SEND 13\r",
            b"HCHAT1 hello!",
            b"AT+RECV 768\r",
            b"ATH\r",
        ):
            reply = relay.feed(step)
            print(f"> {step!r}")
            print(f"< {reply!r}")
        return 0

    if args.connect is not None:
        return run_socket(relay, args.connect)

    if args.stdio:
        return _run_stdio(relay)

    parser.print_help()
    print(
        f"\nstate: enabled={int(relay.enabled)} "
        f"allow={list(relay.allow_list) or 'deny-all'}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
