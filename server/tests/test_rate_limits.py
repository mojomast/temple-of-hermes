from __future__ import annotations

from dataclasses import replace

import pytest

from hbbs.config import RateLimit
from hbbs.errors import HBBSError
from hbbs.service import HBBSService

from conftest import active_user, make_config


def test_agent_limits_are_stricter_than_human_limits(tmp_path, clock):
    limits = {
        "post_human": RateLimit(3, 600),
        "post_agent": RateLimit(1, 600),
        "post_sysop": RateLimit(100, 600),
        "read_human": RateLimit(500, 60),
        "read_agent": RateLimit(500, 60),
        "flag_human": RateLimit(20, 3600),
        "flag_agent": RateLimit(20, 3600),
    }
    service = HBBSService(make_config(tmp_path, limits=limits), clock=clock)
    sysop = service.login({"username": "root", "password": "correct horse battery staple"})
    alice = active_user(service, sysop, "alice")
    active_user(service, sysop, "owner")
    helper = active_user(service, sysop, "helper", kind="agent", owner="owner")

    for index in range(3):
        service.create_post(alice, "general", {"subject": f"human {index}", "body": "x"})
    with pytest.raises(HBBSError) as exc:
        service.create_post(alice, "general", {"subject": "human 4", "body": "x"})
    assert exc.value.code == "rate_limited"
    assert exc.value.details["retry_after_seconds"] > 0

    service.create_post(helper, "general", {"subject": "agent 1", "body": "x"})
    with pytest.raises(HBBSError) as exc:
        service.create_post(helper, "general", {"subject": "agent 2", "body": "x"})
    assert exc.value.code == "rate_limited"

    clock.advance(601)
    service.create_post(helper, "general", {"subject": "agent after window", "body": "x"})


def test_limits_are_per_account(tmp_path, clock):
    limits = {
        "post_human": RateLimit(1, 600),
        "post_agent": RateLimit(1, 600),
        "post_sysop": RateLimit(100, 600),
        "read_human": RateLimit(500, 60),
        "read_agent": RateLimit(500, 60),
        "flag_human": RateLimit(20, 3600),
        "flag_agent": RateLimit(20, 3600),
    }
    service = HBBSService(make_config(tmp_path, limits=limits), clock=clock)
    sysop = service.login({"username": "root", "password": "correct horse battery staple"})
    alice = active_user(service, sysop, "alice")
    bob = active_user(service, sysop, "bob")
    service.create_post(alice, "general", {"subject": "a", "body": "x"})
    service.create_post(bob, "general", {"subject": "b", "body": "x"})
    with pytest.raises(HBBSError):
        service.create_post(alice, "general", {"subject": "a2", "body": "x"})


def test_zero_limit_blocks_immediately(tmp_path, clock):
    limits = {
        "post_human": RateLimit(0, 600),
        "post_agent": RateLimit(0, 600),
        "post_sysop": RateLimit(100, 600),
        "read_human": RateLimit(500, 60),
        "read_agent": RateLimit(500, 60),
        "flag_human": RateLimit(20, 3600),
        "flag_agent": RateLimit(20, 3600),
    }
    service = HBBSService(make_config(tmp_path, limits=limits), clock=clock)
    sysop = service.login({"username": "root", "password": "correct horse battery staple"})
    alice = active_user(service, sysop, "alice")
    with pytest.raises(HBBSError) as exc:
        service.create_post(alice, "general", {"subject": "a", "body": "x"})
    assert exc.value.code == "rate_limited"
