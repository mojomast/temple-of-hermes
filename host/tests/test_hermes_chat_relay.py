"""Tests for the Temple of Hermes COM2 chat relay.

All tests are in-memory.  Nothing opens a socket, serial port, or network
resource, and no test depends on a running guest.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import hermes_chat_relay as relay_mod
from hermes_chat_relay import (
    ERR_PREFIX,
    PREFIX,
    CallableResponder,
    HermesChatRelay,
    HermesResponder,
    ScriptedResponder,
    encode_frame,
)


def make_relay(**kwargs):
    kwargs.setdefault("allow_list", ["hermes"])
    return HermesChatRelay(**kwargs)


def send_frame(relay: HermesChatRelay, text: str) -> bytes:
    payload = encode_frame(text)
    assert relay.feed(f"AT+SEND {len(payload)}\r".encode("ascii")) == b""
    return relay.feed(payload)


def read_frame(relay: HermesChatRelay) -> bytes:
    response = relay.feed(b"AT+RECV 768\r")
    assert response.startswith(b"DATA ")
    head, data = response.split(b"\r\n", 1)
    size = int(head.split()[1])
    assert size == len(data)
    return data


def test_networking_is_off_by_default():
    relay = make_relay()
    assert relay.enabled is False
    assert relay.connected is False
    assert relay.command("ATD hermes") == "ERROR"
    assert relay.connected is False
    assert relay.queued_bytes == 0


def test_empty_allow_list_denies_everything():
    relay = make_relay(enabled=True, allow_list=[])
    assert relay.command("ATD hermes") == "ERROR"
    assert relay.connected is False


def test_allow_list_denies_unknown_destination():
    relay = make_relay(enabled=True, allow_list=["hermes"])
    assert relay.command("ATD elsewhere") == "ERROR"
    assert relay.connected is False


def test_fake_dial_connects_allow_listed_destination():
    relay = make_relay(enabled=True, allow_list=["hermes"])
    assert relay.command("ATD hermes") == "CONNECT hermes"
    assert relay.connected_to == "hermes"


def test_allow_list_matching_is_case_insensitive():
    relay = make_relay(enabled=True, allow_list=["HERMES"])
    assert relay.command("ATD Hermes") == "CONNECT hermes"
    assert relay.connected_to == "hermes"


@pytest.mark.parametrize(
    "command",
    ["ATD hermes", "ATDT hermes", "ATDP hermes", "ATDhermes"],
)
def test_dial_argument_forms(command):
    relay = make_relay(enabled=True)
    assert relay.command(command) == "CONNECT hermes"


def test_named_destination_beginning_with_p_is_not_stripped():
    relay = make_relay(enabled=True, allow_list=["phone"])
    assert relay.command("ATDphone") == "CONNECT phone"


def test_at_atz_and_ath_basics():
    relay = make_relay(enabled=True)
    assert relay.command("AT") == "OK"
    assert relay.command("ATZ") == "OK"
    assert relay.command("ATH") == "OK"

    assert relay.command("ATD hermes") == "CONNECT hermes"
    assert relay.connected is True
    assert relay.command("ATH") == "OK"
    assert relay.connected is False


def test_unknown_command_errors():
    relay = make_relay(enabled=True)
    assert relay.command("AT+WAT") == "ERROR"
    assert relay.command("NONSENSE") == "ERROR"


def test_send_requires_a_connection():
    relay = make_relay(enabled=True)
    assert relay.command("AT+SEND 3") == "ERROR"
    assert relay.queued_bytes == 0


def test_chat_roundtrip():
    relay = make_relay(enabled=True, responder=ScriptedResponder(["hello back"]))
    assert relay.command("ATD hermes") == "CONNECT hermes"

    assert send_frame(relay, "hello hermes") == b"OK 19\r\n"
    assert read_frame(relay) == (PREFIX + "hello back").encode()


def test_ping_gets_pong_from_default_responder():
    relay = make_relay(enabled=True, responder=HermesResponder())
    assert relay.command("ATD hermes") == "CONNECT hermes"
    send_frame(relay, "ping")
    assert read_frame(relay) == b"HCHAT1 pong"


def test_empty_recv_is_an_empty_frame():
    relay = make_relay(enabled=True)
    assert relay.command("ATD hermes") == "CONNECT hermes"
    assert relay.feed(b"AT+RECV 16\r") == b"DATA 0\r\n"


def test_malformed_frame_queues_protocol_error():
    relay = make_relay(enabled=True)
    assert relay.command("ATD hermes") == "CONNECT hermes"
    payload = b"not-a-frame"
    assert relay.feed(f"AT+SEND {len(payload)}\r".encode()) == b""
    assert relay.feed(payload) == f"OK {len(payload)}".encode() + b"\r\n"
    assert read_frame(relay).startswith(ERR_PREFIX.encode())


def test_responder_failure_queues_protocol_error():
    def boom(_text: str) -> str:
        raise RuntimeError("no agent")

    relay = make_relay(enabled=True, responder=CallableResponder(boom))
    assert relay.command("ATD hermes") == "CONNECT hermes"
    send_frame(relay, "hello")
    frame = read_frame(relay)
    assert frame.startswith(ERR_PREFIX.encode())
    assert b"responder failed" in frame


def test_send_and_recv_disabled_when_modem_off():
    relay = make_relay(enabled=False)
    assert relay.command("AT+SEND 3") == "ERROR"
    assert relay.command("AT+RECV 3") == "ERROR"
    assert relay.queued_bytes == 0


def test_denied_send_payload_is_not_parsed_as_commands():
    relay = make_relay(enabled=True)
    assert relay.feed(b"AT+SEND 13\r") == b"ERROR\r\n"
    assert relay.feed(b"ATD hermes\rXX") == b""
    assert relay.connected is False
    assert relay.feed(b"AT\r") == b"OK\r\n"


def test_fragmented_and_multiple_commands():
    relay = make_relay(enabled=True)
    assert relay.feed(b"AT\r") == b"OK\r\n"
    assert relay.feed(b"ATD her") == b""
    assert relay.feed(b"mes\r") == b"CONNECT hermes\r\n"
    assert relay.feed(b"AT\rAT\r") == b"OK\r\nOK\r\n"


def test_status_reports_state_without_secrets():
    relay = make_relay(enabled=True)
    assert relay.command("AT+STATUS") == (
        "STATUS enabled=1 connected=0 dest=- allow=1 queued=0"
    )
    assert relay.command("ATD hermes") == "CONNECT hermes"
    assert relay.command("AT+STATUS") == (
        "STATUS enabled=1 connected=1 dest=hermes allow=1 queued=0"
    )


def test_commands_are_logged_without_chat_payload(tmp_path):
    log = tmp_path / "relay.log"
    relay = make_relay(enabled=True, log_path=log)
    assert relay.command("ATD hermes") == "CONNECT hermes"
    send_frame(relay, "secret message")
    read_frame(relay)

    text = log.read_text(encoding="utf-8")
    assert "CMD ATD hermes" in text
    assert "DIAL dest=hermes result=connect" in text
    assert "CHAT text=" not in text
    assert "secret message" not in text
    assert "CHAT bytes=" in text


def test_log_messages_is_opt_in(tmp_path):
    log = tmp_path / "relay.log"
    relay = make_relay(enabled=True, log_path=log, log_messages=True)
    assert relay.command("ATD hermes") == "CONNECT hermes"
    send_frame(relay, "visible")
    assert "visible" in log.read_text(encoding="utf-8")


def test_encode_frame_is_single_line():
    assert encode_frame("a\nb\r\nc") == b"HCHAT1 a b  c"


def test_demo_cli_runs_in_memory(capsys):
    assert relay_mod.main(["--demo"]) == 0
    out = capsys.readouterr().out
    assert "CONNECT hermes" in out
    assert "pong" not in out
