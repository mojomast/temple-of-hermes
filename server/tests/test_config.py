from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from hbbs.config import Config


def test_defaults_are_loopback_and_environment_driven(tmp_path):
    config = Config.from_env({"HBBS_DATA_DIR": str(tmp_path)})
    assert config.bind_host == "127.0.0.1"
    assert config.bind_port == 8443
    assert config.db_path == str(tmp_path / "hbbs.sqlite3")
    assert config.tls_enabled is False
    config.check_bind_safety()


def test_every_network_setting_comes_from_environment(tmp_path):
    config = Config.from_env(
        {
            "HBBS_BIND_HOST": "127.0.0.1",
            "HBBS_BIND_PORT": "9443",
            "HBBS_TLS_CERT": "/tmp/example.crt",
            "HBBS_TLS_KEY": "/tmp/example.key",
            "HBBS_DATA_DIR": str(tmp_path),
            "HBBS_TOKEN_TTL_SECONDS": "120",
            "HBBS_SIGNUP_MODE": "closed",
            "HBBS_POST_MODERATION": "yes",
        }
    )
    assert config.bind_port == 9443
    assert config.tls_enabled is True
    assert config.token_ttl_seconds == 120
    assert config.signup_mode == "closed"
    assert config.post_moderation is True


def test_tls_requires_both_cert_and_key():
    with pytest.raises(ValueError):
        Config.from_env({"HBBS_TLS_CERT": "/tmp/example.crt"})


def test_plaintext_non_loopback_bind_is_refused():
    config = Config.from_env({"HBBS_BIND_HOST": "0.0.0.0"})
    with pytest.raises(ValueError):
        config.check_bind_safety()
    config = Config.from_env({"HBBS_BIND_HOST": "0.0.0.0", "HBBS_ALLOW_INSECURE_BIND": "1"})
    config.check_bind_safety()


def test_tls_non_loopback_bind_is_allowed():
    config = Config.from_env(
        {
            "HBBS_BIND_HOST": "0.0.0.0",
            "HBBS_TLS_CERT": "/tmp/example.crt",
            "HBBS_TLS_KEY": "/tmp/example.key",
        }
    )
    config.check_bind_safety()


def test_auto_signup_mode_and_kind_list(tmp_path):
    config = Config.from_env(
        {
            "HBBS_DATA_DIR": str(tmp_path),
            "HBBS_SIGNUP_MODE": "auto",
            "HBBS_AUTO_APPROVE_KINDS": " human , , agent , human ",
        }
    )
    assert config.signup_mode == "auto"
    assert config.auto_approve_kinds == ("human", "agent")

    default = Config.from_env({"HBBS_DATA_DIR": str(tmp_path)})
    assert default.signup_mode == "auto"
    moderated = Config.from_env({"HBBS_DATA_DIR": str(tmp_path), "HBBS_SIGNUP_MODE": "open"})
    assert moderated.signup_mode == "open"
    assert default.auto_approve_kinds == ("human", "agent")

    selected = Config.from_env(
        {"HBBS_DATA_DIR": str(tmp_path), "HBBS_AUTO_APPROVE_KINDS": "agent,"}
    )
    assert selected.auto_approve_kinds == ("agent",)


def test_unknown_auto_approve_kind_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        Config.from_env(
            {"HBBS_DATA_DIR": str(tmp_path), "HBBS_AUTO_APPROVE_KINDS": "human,robot"}
        )


def test_bad_values_fail_closed():
    with pytest.raises(ValueError):
        Config.from_env({"HBBS_BIND_PORT": "70000"})
    with pytest.raises(ValueError):
        Config.from_env({"HBBS_SIGNUP_MODE": "sometimes"})
    with pytest.raises(ValueError):
        Config.from_env({"HBBS_TOKEN_TTL_SECONDS": "0"})
    with pytest.raises(ValueError):
        Config.from_env({"HBBS_RATE_POST_HUMAN": "lots"})


def test_rate_limit_environment_knobs(tmp_path):
    config = Config.from_env(
        {
            "HBBS_DATA_DIR": str(tmp_path),
            "HBBS_RATE_POST_HUMAN": "7",
            "HBBS_RATE_POST_AGENT": "2",
        }
    )
    assert config.limits["post_human"].limit == 7
    assert config.limits["post_agent"].limit == 2


def test_closed_signup_refuses_new_accounts(tmp_path):
    from hbbs.errors import HBBSError
    from hbbs.service import HBBSService

    config = replace(Config.from_env({"HBBS_DATA_DIR": str(tmp_path)}), signup_mode="closed")
    service = HBBSService(config)
    with pytest.raises(HBBSError) as exc:
        service.signup({"username": "alice", "password": "a sufficiently long password"})
    assert exc.value.code == "signup_closed"


def test_in_memory_database_is_supported_for_in_process_tests():
    from hbbs.service import HBBSService

    config = replace(Config.from_env({}), db_path=":memory:", sysop_username="root", sysop_password="correct horse battery staple")
    service = HBBSService(config)
    sysop = service.login({"username": "root", "password": "correct horse battery staple"})
    assert sysop["token"]
    assert service.list_boards()["boards"][0]["name"] == "general"
