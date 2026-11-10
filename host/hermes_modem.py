#!/usr/bin/env python3
"""Hayes-style AT modem for the Temple of Hermes COM2 link.

The modem is deliberately inert until a caller both enables it and supplies a
transport.  Only destinations named in an explicit allow-list may be dialed.
Every command, denial and result is written to an optional log file; payload
bytes are never logged.

Typical host-side wiring::

    modem = HermesModem(
        enabled=True,
        allow_list=("hermes",),
        transport=MyTransport(),
        log_path=Path("modem.log"),
    )

    # The guest writes AT commands on COM2.  The host feeds those bytes in and
    # writes the returned bytes back to the serial port.
    reply = modem.feed(b"ATD hermes\\r")

The guest side lives in ``Hermes/Net`` and uses COM2 (0x2F8, IRQ 3).

Commands implemented
-------------------
AT, ATZ / AT&F, ATI, ATE0 / ATE1, ATD<dest>, ATH, AT+STATUS,
AT+SEND <len> (followed by exactly <len> raw bytes), AT+RECV <max>.

``AT+SEND`` and ``AT+RECV`` are small Hermes extensions used by the guest
library so that binary payloads never have to pass through a Hayes ``+++``
escape in the middle of data.
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
    "FakeTransport",
    "HermesModem",
    "LoopbackTransport",
    "ModemError",
    "NullTransport",
    "Transport",
]

CRLF = b"\r\n"
DEFAULT_BAUD = 115200
MAX_SEND = 1 << 20
MAX_RECV = 1 << 16


class ModemError(RuntimeError):
    """Raised by a transport when it cannot satisfy a modem request."""


class Transport(Protocol):
    """Network side of the modem.

    A real implementation might open a TCP/Unix socket, a serial link to a
    radio, or a test double.  Tests use :class:`FakeTransport`, which never
    touches the network.
    """

    def connect(self, destination: str) -> None:
        ...

    def send(self, data: bytes) -> int:
        ...

    def recv(self, max_bytes: int, timeout: float | None = None) -> bytes:
        ...

    def disconnect(self) -> None:
        ...


class NullTransport:
    """Default transport: accepts no dial tone and never opens a network."""

    def connect(self, destination: str) -> None:
        raise ModemError("no transport configured")

    def send(self, data: bytes) -> int:
        raise ModemError("no transport configured")

    def recv(self, max_bytes: int, timeout: float | None = None) -> bytes:
        return b""

    def disconnect(self) -> None:
        return None


class FakeTransport:
    """In-memory transport for tests.  It performs no I/O."""

    def __init__(
        self,
        inbox: bytes = b"",
        connect_error: BaseException | None = None,
    ) -> None:
        self.inbox = bytearray(inbox)
        self.sent = bytearray()
        self.destination: str | None = None
        self.connect_calls: list[str] = []
        self.disconnect_calls = 0
        self.connect_error = connect_error

    @property
    def connected(self) -> bool:
        return self.destination is not None

    def connect(self, destination: str) -> None:
        self.connect_calls.append(destination)
        if self.connect_error is not None:
            raise self.connect_error
        self.destination = destination

    def send(self, data: bytes) -> int:
        if not self.connected:
            raise ModemError("not connected")
        self.sent.extend(data)
        return len(data)

    def recv(self, max_bytes: int, timeout: float | None = None) -> bytes:
        if not self.connected or max_bytes <= 0:
            return b""
        out = bytes(self.inbox[:max_bytes])
        del self.inbox[: len(out)]
        return out

    def disconnect(self) -> None:
        self.disconnect_calls += 1
        self.destination = None


class LoopbackTransport:
    """Manual-test transport: everything sent comes back on receive."""

    def __init__(self) -> None:
        self.inbox = bytearray()
        self.destination: str | None = None

    def connect(self, destination: str) -> None:
        self.destination = destination

    def send(self, data: bytes) -> int:
        if self.destination is None:
            raise ModemError("not connected")
        self.inbox.extend(data)
        return len(data)

    def recv(self, max_bytes: int, timeout: float | None = None) -> bytes:
        if self.destination is None or max_bytes <= 0:
            return b""
        out = bytes(self.inbox[:max_bytes])
        del self.inbox[: len(out)]
        return out

    def disconnect(self) -> None:
        self.destination = None


class HermesModem:
    """Line-oriented Hayes AT emulator with an explicit allow-list.

    Parameters
    ----------
    enabled:
        Networking is off by default.  While false, ``ATD``, ``AT+SEND`` and
        ``AT+RECV`` answer ``ERROR`` and the transport is never used.
    allow_list:
        Destinations that may be dialed.  Matching is case-insensitive and
        exact.  An empty allow-list denies every destination.
    transport:
        Network-side implementation.  Defaults to :class:`NullTransport`.
    log_path:
        Optional file that receives command/result lines.  Payload bytes are
        not logged.
    logger:
        Optional callable receiving one log line at a time.
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        allow_list: Iterable[str] = (),
        transport: Transport | None = None,
        log_path: str | Path | None = None,
        logger: Callable[[str], None] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.enabled = bool(enabled)
        self.allow_list = tuple(str(d).strip().lower() for d in allow_list if str(d).strip())
        self.transport: Transport = transport if transport is not None else NullTransport()
        self.log_path = Path(log_path) if log_path is not None else None
        self._logger = logger
        self._clock = clock
        self.connected_to: str | None = None
        self.echo = False
        self._buf = bytearray()
        self._pending_send: int | None = None
        self._pending_discard: int | None = None
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ state
    @property
    def connected(self) -> bool:
        return self.connected_to is not None

    def is_allowed(self, destination: str) -> bool:
        return destination.strip().lower() in self.allow_list

    # ----------------------------------------------------------------- logging
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

    # --------------------------------------------------------------- commands
    def reset(self) -> None:
        self._hangup()
        self._buf.clear()
        self._pending_send = None
        self._pending_discard = None

    def _hangup(self) -> None:
        if self.connected_to is not None:
            try:
                self.transport.disconnect()
            except Exception:
                pass
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
        try:
            self.transport.connect(key)
        except Exception as exc:
            self._log("DIAL", f"dest={key} result=no-carrier reason={type(exc).__name__}")
            return b"NO CARRIER" + CRLF
        self.connected_to = key
        self._log("DIAL", f"dest={key} result=connect")
        return b"CONNECT " + key.encode("ascii", "replace") + CRLF

    def _send(self, payload: bytes) -> bytes:
        if not self.enabled or not self.connected:
            self._log("DENY", "send not-connected-or-disabled")
            return b"ERROR" + CRLF
        try:
            sent = self.transport.send(payload)
        except Exception:
            self._log("SEND", "result=error")
            return b"ERROR" + CRLF
        sent = len(payload) if sent is None else int(sent)
        self._log("SEND", f"bytes={sent}")
        return f"OK {sent}".encode("ascii") + CRLF

    def _recv(self, maximum: int) -> bytes:
        if not self.enabled or not self.connected:
            self._log("DENY", "recv not-connected-or-disabled")
            return b"ERROR" + CRLF
        maximum = max(0, min(maximum, MAX_RECV))
        try:
            data = self.transport.recv(maximum, timeout=0)
        except Exception:
            self._log("RECV", "result=error")
            return b"ERROR" + CRLF
        if data is None:
            data = b""
        data = bytes(data)
        self._log("RECV", f"bytes={len(data)}")
        return f"DATA {len(data)}".encode("ascii") + CRLF + data

    def _status(self) -> bytes:
        state = self.connected_to or "-"
        return (
            f"STATUS enabled={int(self.enabled)} connected={int(self.connected)} "
            f"dest={state} allow={len(self.allow_list)}"
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
            return b"Temple of Hermes modem" + CRLF
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
        # Hayes puts T (tone) or P (pulse) before a phone number.  Only strip
        # that letter when it is clearly a dial modifier, not the first letter
        # of a named destination such as "phone".
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
            # Consume the announced payload so its bytes cannot be parsed as
            # fresh AT commands.
            self._pending_discard = length
            return b"ERROR" + CRLF
        if length == 0:
            return self._send(b"")
        self._pending_send = length
        return b""

    # -------------------------------------------------------------- byte pump
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
                out += self._send(payload)
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
        """Convenience wrapper for one command; returns the ASCII response."""
        if not text.endswith("\r") and not text.endswith("\n"):
            text += "\r"
        return self.feed(text.encode("ascii", "replace")).decode("ascii", "replace").strip()


def _run_stdio(modem: HermesModem) -> int:
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    while True:
        chunk = stdin.read(4096)
        if not chunk:
            return 0
        reply = modem.feed(chunk)
        if reply:
            stdout.write(reply)
            stdout.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Temple of Hermes COM2 Hayes modem (off by default, allow-list only)"
    )
    parser.add_argument(
        "--enable",
        action="store_true",
        help="enable dialing (networking stays off without this flag)",
    )
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="DEST",
        help="add DEST to the allow-list (repeatable; default is deny-all)",
    )
    parser.add_argument("--log", type=Path, default=None, help="append command log here")
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="bridge AT bytes between stdin and stdout",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="run a loopback self-test and print the transcript",
    )
    args = parser.parse_args(argv)

    if args.demo:
        modem = HermesModem(
            enabled=args.enable,
            allow_list=args.allow or ["hermes"],
            transport=LoopbackTransport(),
            log_path=args.log,
        )
        for cmd in ("AT", "ATZ", "ATD hermes", "AT+SEND 5", "hello", "AT+RECV 16", "ATH"):
            if cmd == "hello":
                reply = modem.feed(b"hello")
            else:
                reply = modem.feed(cmd.encode("ascii") + b"\r")
            print(f"> {cmd}")
            print(f"< {reply!r}")
        return 0

    modem = HermesModem(
        enabled=args.enable,
        allow_list=args.allow,
        transport=LoopbackTransport(),
        log_path=args.log,
    )
    if args.stdio:
        return _run_stdio(modem)

    parser.print_help()
    print(
        f"\nstate: enabled={int(modem.enabled)} allow={list(modem.allow_list) or 'deny-all'}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
