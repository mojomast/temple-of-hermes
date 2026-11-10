"""HBBS/1 framing and body codec.

The wire format is one ASCII header line followed by an exact-length JSON body.
This module is deliberately strict: a malformed header, a forbidden byte, a
duplicate JSON key, a float, or too much nesting is rejected instead of being
coerced. Nothing here interprets board content; it only moves bytes.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, BinaryIO

from .errors import BBS1Error

MAGIC = "HBBS/1"
MAX_HEADER_BYTES = 128
MAX_BODY_BYTES = 16_384
MAX_JSON_DEPTH = 8
TYPES = {"REQ", "RSP"}

ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,32}$")
COMMAND_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,15}$")
LENGTH_RE = re.compile(r"^(0|[1-9][0-9]{0,4})$")
HEADER_RE = re.compile(
    r"^HBBS/1 (?P<type>REQ|RSP) (?P<id>[A-Za-z0-9._-]{1,32}) "
    r"(?P<command>[A-Z][A-Z0-9_]{0,15}) (?P<length>[0-9]{1,5})$"
)


class FrameError(BBS1Error):
    """A framing/body error that carries enough header data to correlate."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        frame_id: str | None = None,
        command: str | None = None,
        field: str | None = None,
    ) -> None:
        super().__init__(code, message, field=field)
        self.frame_id = frame_id
        self.command = command


@dataclass(frozen=True)
class Frame:
    type: str
    id: str
    command: str
    length: int
    body: dict[str, Any]
    raw_body: bytes


class _DuplicateKey(ValueError):
    pass


class _Float(ValueError):
    pass


class _Constant(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateKey(key)
        value[key] = item
    return value


def _no_float(_value: str) -> Any:
    raise _Float()


def _no_constant(_value: str) -> Any:
    raise _Constant()


def _check_depth(value: Any, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise FrameError("invalid_field", "JSON nesting is too deep")
    if isinstance(value, dict):
        for item in value.values():
            _check_depth(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _check_depth(item, depth + 1)


def _check_printable(raw: bytes) -> None:
    for byte in raw:
        if byte < 0x20 or byte > 0x7E:
            raise FrameError("not_printable_ascii", "body must be printable ASCII")


def decode_body(raw: bytes, *, frame_id: str | None = None, command: str | None = None) -> dict[str, Any]:
    if len(raw) > MAX_BODY_BYTES:
        raise FrameError("body_too_large", "body exceeds the frame limit", frame_id=frame_id, command=command)
    _check_printable(raw)
    try:
        text = raw.decode("ascii")
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_float=_no_float,
            parse_constant=_no_constant,
        )
    except _DuplicateKey as exc:
        raise FrameError("invalid_field", "duplicate JSON key", frame_id=frame_id, command=command, field="request") from exc
    except (_Float, _Constant) as exc:
        raise FrameError("invalid_field", "floating-point and non-finite numbers are not allowed", frame_id=frame_id, command=command, field="request") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FrameError("malformed_json", "body is not one JSON object", frame_id=frame_id, command=command, field="request") from exc
    except RecursionError as exc:
        raise FrameError("invalid_field", "JSON nesting is too deep", frame_id=frame_id, command=command, field="request") from exc
    if not isinstance(value, dict):
        raise FrameError("malformed_json", "body is not one JSON object", frame_id=frame_id, command=command, field="request")
    try:
        _check_depth(value)
    except FrameError as exc:
        raise FrameError(exc.code, exc.message, frame_id=frame_id, command=command, field="request") from exc
    return value


def parse_header(line: bytes) -> tuple[str, str, str, int]:
    if not line.endswith(b"\n"):
        raise FrameError("bad_header", "header must end with one LF")
    if len(line) > MAX_HEADER_BYTES:
        raise FrameError("bad_header", "header is too long")
    payload = line[:-1]
    if b"\r" in payload or b"\t" in payload:
        raise FrameError("bad_header", "header contains a forbidden byte")
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as exc:
        raise FrameError("bad_header", "header must be ASCII") from exc
    if text.endswith(" ") or "  " in text:
        raise FrameError("bad_header", "header spacing is invalid")
    match = HEADER_RE.fullmatch(text)
    if match is None:
        raise FrameError("bad_header", "header syntax is invalid")
    frame_type = match.group("type")
    frame_id = match.group("id")
    command = match.group("command")
    length_text = match.group("length")
    if frame_type not in TYPES:
        raise FrameError("bad_header", "header type is invalid", frame_id=frame_id, command=command)
    if ID_RE.fullmatch(frame_id) is None:
        raise FrameError("bad_header", "request id is invalid", command=command)
    if COMMAND_RE.fullmatch(command) is None:
        raise FrameError("bad_header", "command is invalid", frame_id=frame_id)
    if LENGTH_RE.fullmatch(length_text) is None:
        raise FrameError("bad_length", "length is invalid", frame_id=frame_id, command=command)
    length = int(length_text)
    if length > MAX_BODY_BYTES:
        raise FrameError("body_too_large", "body exceeds the frame limit", frame_id=frame_id, command=command)
    return frame_type, frame_id, command, length


def read_frame(stream: BinaryIO) -> Frame:
    line = stream.readline(MAX_HEADER_BYTES + 1)
    if line == b"":
        raise EOFError
    try:
        frame_type, frame_id, command, length = parse_header(line)
    except FrameError as exc:
        raise exc
    raw = stream.read(length)
    if len(raw) != length:
        raise FrameError("bad_length", "body is shorter than the declared length", frame_id=frame_id, command=command)
    body = decode_body(raw, frame_id=frame_id, command=command)
    return Frame(frame_type, frame_id, command, length, body, raw)


def encode_body(body: dict[str, Any]) -> bytes:
    text = json.dumps(body, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    raw = text.encode("ascii")
    if len(raw) > MAX_BODY_BYTES:
        raise BBS1Error("body_too_large", "response body exceeds the frame limit")
    return raw


def encode_frame(command: str, body: dict[str, Any], *, frame_id: str, frame_type: str = "RSP") -> bytes:
    if frame_type not in TYPES:
        raise ValueError("frame type must be REQ or RSP")
    raw = encode_body(body)
    header = f"{MAGIC} {frame_type} {frame_id} {command} {len(raw)}\n".encode("ascii")
    if len(header) > MAX_HEADER_BYTES:
        raise BBS1Error("bad_header", "response header is too long")
    return header + raw


def error_frame(error: BBS1Error, *, frame_id: str, command: str) -> bytes:
    return encode_frame(command, error.envelope(command), frame_id=frame_id)
