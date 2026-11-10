"""Tests for the Temple of Hermes COM2 Hayes modem.

Everything here uses :class:`hermes_modem.FakeTransport`; no test opens a
socket, serial port, or any other real network resource.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import hermes_modem as hm


def make_modem(**kwargs):
    fake = kwargs.pop("fake", None) or hm.FakeTransport()
    kwargs.setdefault("allow_list", ["hermes"])
    return hm.HermesModem(transport=fake, **kwargs), fake


def test_networking_is_off_by_default():
    modem, fake = make_modem()
    assert modem.enabled is False
    assert modem.connected is False

    assert modem.command("ATD hermes") == "ERROR"
    assert fake.connect_calls == []
    assert modem.connected is False


def test_allow_list_denies_unknown_destination():
    modem, fake = make_modem(enabled=True, allow_list=["hermes"])

    assert modem.command("ATD elsewhere") == "ERROR"
    assert fake.connect_calls == []
    assert modem.connected is False


def test_empty_allow_list_denies_everything():
    modem, fake = make_modem(enabled=True, allow_list=[])

    assert modem.command("ATD hermes") == "ERROR"
    assert fake.connect_calls == []


def test_fake_dial_connects_allow_listed_destination():
    modem, fake = make_modem(enabled=True, allow_list=["hermes"])

    assert modem.command("ATD hermes") == "CONNECT hermes"
    assert fake.connect_calls == ["hermes"]
    assert fake.destination == "hermes"
    assert modem.connected_to == "hermes"


def test_allow_list_matching_is_case_insensitive():
    modem, fake = make_modem(enabled=True, allow_list=["HERMES"])

    assert modem.command("ATD Hermes") == "CONNECT hermes"
    assert fake.destination == "hermes"


def test_at_atz_and_ath_basics():
    modem, fake = make_modem(enabled=True)

    assert modem.command("AT") == "OK"
    assert modem.command("ATZ") == "OK"
    assert modem.command("ATH") == "OK"

    assert modem.command("ATD hermes") == "CONNECT hermes"
    assert modem.connected is True

    assert modem.command("ATH") == "OK"
    assert modem.connected is False
    assert fake.disconnect_calls == 1


def test_atz_hangs_up_and_clears_state():
    modem, fake = make_modem(enabled=True)
    assert modem.command("ATD hermes") == "CONNECT hermes"

    assert modem.command("ATZ") == "OK"
    assert modem.connected is False
    assert fake.disconnect_calls == 1


def test_unknown_command_errors():
    modem, _ = make_modem(enabled=True)
    assert modem.command("AT+WAT") == "ERROR"
    assert modem.command("NONSENSE") == "ERROR"


def test_send_requires_a_connection():
    modem, fake = make_modem(enabled=True)
    assert modem.command("AT+SEND 3") == "ERROR"
    assert fake.sent == b""


def test_send_forwards_exact_payload():
    modem, fake = make_modem(enabled=True)
    assert modem.command("ATD hermes") == "CONNECT hermes"

    assert modem.feed(b"AT+SEND 5\r") == b""
    assert modem.feed(b"hello") == b"OK 5\r\n"
    assert fake.sent == b"hello"


def test_send_payload_may_contain_crlf():
    modem, fake = make_modem(enabled=True)
    assert modem.command("ATD hermes") == "CONNECT hermes"

    assert modem.feed(b"AT+SEND 4\r") == b""
    assert modem.feed(b"a\r\nb") == b"OK 4\r\n"
    assert fake.sent == b"a\r\nb"


def test_recv_returns_data_frame():
    fake = hm.FakeTransport(inbox=b"world")
    modem, _ = make_modem(enabled=True, fake=fake)
    assert modem.command("ATD hermes") == "CONNECT hermes"

    assert modem.feed(b"AT+RECV 16\r") == b"DATA 5\r\nworld"


def test_recv_with_no_data_is_empty_frame():
    modem, _ = make_modem(enabled=True)
    assert modem.command("ATD hermes") == "CONNECT hermes"

    assert modem.feed(b"AT+RECV 16\r") == b"DATA 0\r\n"


def test_send_and_recv_disabled_when_modem_off():
    modem, fake = make_modem(enabled=False)
    assert modem.command("AT+SEND 3") == "ERROR"
    assert modem.command("AT+RECV 3") == "ERROR"
    assert fake.sent == b""


def test_fragmented_and_multiple_commands():
    modem, fake = make_modem(enabled=True)

    assert modem.feed(b"AT\r") == b"OK\r\n"
    assert modem.feed(b"ATD her") == b""
    assert modem.feed(b"mes\r") == b"CONNECT hermes\r\n"
    assert modem.feed(b"AT\rAT\r") == b"OK\r\nOK\r\n"


def test_transport_failure_reports_no_carrier():
    fake = hm.FakeTransport(connect_error=hm.ModemError("dial failed"))
    modem, _ = make_modem(enabled=True, fake=fake)

    assert modem.command("ATD hermes") == "NO CARRIER"
    assert modem.connected is False


def test_status_reports_state_without_secrets():
    modem, _ = make_modem(enabled=True)
    assert modem.command("AT+STATUS") == (
        "STATUS enabled=1 connected=0 dest=- allow=1"
    )
    assert modem.command("ATD hermes") == "CONNECT hermes"
    assert modem.command("AT+STATUS") == (
        "STATUS enabled=1 connected=1 dest=hermes allow=1"
    )


def test_commands_are_logged_without_payload(tmp_path):
    log = tmp_path / "modem.log"
    modem, _ = make_modem(enabled=True, log_path=log)

    assert modem.command("ATD hermes") == "CONNECT hermes"
    assert modem.feed(b"AT+SEND 6\r") == b""
    assert modem.feed(b"secret") == b"OK 6\r\n"

    text = log.read_text(encoding="utf-8")
    assert "CMD ATD hermes" in text
    assert "DIAL dest=hermes result=connect" in text
    assert "SEND bytes=6" in text
    assert "secret" not in text


def test_denials_are_logged(tmp_path):
    log = tmp_path / "modem.log"
    modem, _ = make_modem(enabled=True, allow_list=["hermes"], log_path=log)

    assert modem.command("ATD elsewhere") == "ERROR"
    text = log.read_text(encoding="utf-8")
    assert "DENY allow-list dest=elsewhere" in text


@pytest.mark.parametrize(
    "command,expected",
    [
        ("ATD hermes", "CONNECT hermes"),
        ("ATDT hermes", "CONNECT hermes"),
        ("ATDP hermes", "CONNECT hermes"),
        ("ATDhermes", "CONNECT hermes"),
    ],
)
def test_dial_argument_forms(command, expected):
    modem, _ = make_modem(enabled=True)
    assert modem.command(command) == expected


def test_named_destination_beginning_with_p_is_not_stripped():
    modem, fake = make_modem(enabled=True, allow_list=["phone"])
    assert modem.command("ATDphone") == "CONNECT phone"
    assert fake.destination == "phone"


def test_denied_send_payload_is_not_parsed_as_commands():
    modem, fake = make_modem(enabled=True)
    assert modem.feed(b"AT+SEND 13\r") == b"ERROR\r\n"
    assert modem.feed(b"ATD hermes\rXX") == b""
    assert fake.connect_calls == []
    assert modem.feed(b"AT\r") == b"OK\r\n"


def test_invalid_send_length_is_rejected():
    modem, fake = make_modem(enabled=True)
    assert modem.command("ATD hermes") == "CONNECT hermes"
    assert modem.command("AT+SEND nope") == "ERROR"
    assert fake.sent == b""
