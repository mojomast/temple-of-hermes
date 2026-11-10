from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

from hbbs.frames import (
    FrameError,
    decode_body,
    encode_frame,
    parse_header,
    read_frame,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "hbbs1"


def test_manifest_lengths_and_hashes_match_fixture_bytes():
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["fixtures"]:
        for side in ("request", "response"):
            raw = (FIXTURES / entry[f"{side}"]).read_bytes()
            header, body = raw.split(b"\n", 1)
            assert len(body) == entry[f"{side}_body_length"]
            assert hashlib.sha256(raw).hexdigest() == entry[f"{side}_sha256"]
            assert header.startswith(b"HBBS/1 REQ " if side == "request" else b"HBBS/1 RSP ")


def test_every_fixture_frame_is_valid_and_correlated():
    for path in sorted(FIXTURES.glob("*/*.hbbs")):
        raw = path.read_bytes()
        frame = read_frame(io.BytesIO(raw))
        assert frame.type in {"REQ", "RSP"}
        assert frame.length == len(frame.raw_body)
        assert frame.body["v"] == 1
        assert frame.body["command"] == frame.command
        assert set(frame.body) <= {"v", "ok", "command", "args", "data", "error"}


def test_round_trip_encode_and_decode():
    body = {"v": 1, "command": "WHOAMI", "args": {}}
    raw = encode_frame("WHOAMI", body, frame_id="r-1", frame_type="REQ")
    frame = read_frame(io.BytesIO(raw))
    assert frame.id == "r-1"
    assert frame.command == "WHOAMI"
    assert frame.body == body


def test_bad_header_forms_are_rejected():
    for line in (
        b"HBBS/1 REQ r-1 WHOAMI 2\r\n",
        b"HBBS/1 REQ r-1 WHOAMI 02\n",
        b"HBBS/1 REQ r-1 whoami 2\n",
        b"HBBS/1 REQ r-1 WHOAMI  2\n",
        b"HBBS/2 REQ r-1 WHOAMI 2\n",
        b"HBBS/1 REQ r-1 WHOAMI 2 ",
    ):
        with pytest.raises(FrameError):
            parse_header(line)


def test_non_printable_and_oversize_bodies_are_rejected():
    with pytest.raises(FrameError) as exc:
        decode_body(b'{"v":1,"command":"WHOAMI","args":{}}\x00')
    assert exc.value.code == "not_printable_ascii"

    with pytest.raises(FrameError) as exc:
        decode_body(b" " * 16_385)
    assert exc.value.code == "body_too_large"


def test_duplicate_keys_floats_and_deep_nesting_are_rejected():
    with pytest.raises(FrameError) as exc:
        decode_body(b'{"v":1,"v":1,"command":"WHOAMI","args":{}}')
    assert exc.value.code == "invalid_field"

    with pytest.raises(FrameError) as exc:
        decode_body(b'{"v":1,"command":"WHOAMI","args":{"x":1.5}}')
    assert exc.value.code == "invalid_field"

    nested = '{"v":1,"command":"WHOAMI","args":' + "[" * 10 + "]" * 10 + "}"
    with pytest.raises(FrameError) as exc:
        decode_body(nested.encode("ascii"))
    assert exc.value.code == "invalid_field"


def test_response_errors_use_the_nested_hbbs_shape():
    from hbbs.errors import BBS1Error

    error = BBS1Error("rate_limited", "rate limit exceeded", retry_after=7, details={"scope": "requests_burst"})
    body = error.envelope("LIST")
    assert body == {
        "v": 1,
        "ok": False,
        "command": "LIST",
        "error": {
            "code": "rate_limited",
            "message": "rate limit exceeded",
            "retry_after": 7,
            "details": {"scope": "requests_burst"},
        },
    }
