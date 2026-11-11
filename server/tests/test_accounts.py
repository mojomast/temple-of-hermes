from __future__ import annotations

import pytest

from hbbs.errors import HBBSError

from conftest import SYSOP, SYSOP_PASSWORD, active_user, approve, signup


def test_open_signup_enters_moderation_queue_and_cannot_login_yet(service, sysop):
    result = signup(service, "alice", display_name="Alice")
    assert result["status"] == "pending"
    assert result["account"]["status"] == "pending"
    assert result["account"]["display_name"] == "Alice"
    assert result["queue_id"] > 0

    with pytest.raises(HBBSError) as exc:
        service.login({"username": "alice", "password": "a sufficiently long password"})
    assert exc.value.status == 403
    assert exc.value.code == "account_pending"

    queue = service.mod_queue(sysop)
    assert [item["account"]["username"] for item in queue["items"]] == ["alice"]
    item = queue["items"][0]
    resolved = service.resolve_queue(sysop, item["id"], approve=True)
    assert resolved["account"]["status"] == "active"

    login = service.login({"username": "alice", "password": "a sufficiently long password"})
    assert login["token"]
    assert login["token_type"] == "Bearer"
    assert login["account"]["kind"] == "human"


def test_duplicate_username_is_case_insensitive(service):
    signup(service, "Alice")
    with pytest.raises(HBBSError) as exc:
        signup(service, "ALICE")
    assert exc.value.code == "username_taken"


def test_weak_password_and_invalid_username_are_rejected(service):
    with pytest.raises(HBBSError) as exc:
        signup(service, "bob", password="short")
    assert exc.value.code == "weak_password"

    with pytest.raises(HBBSError) as exc:
        signup(service, "not a username")
    assert exc.value.code == "invalid_username"


def test_agent_accounts_are_labeled_and_require_a_human_owner(service, sysop):
    with pytest.raises(HBBSError) as exc:
        signup(service, "helper", kind="agent", owner="missing")
    assert exc.value.code == "invalid_owner"

    active_user(service, sysop, "owner")
    signup(service, "helper", kind="agent", owner="owner")
    approve(service, sysop, "helper")
    login = service.login({"username": "helper", "password": "a sufficiently long password"})
    account = login["account"]
    assert account["kind"] == "agent"
    assert account["agent"] is True
    assert account["label"] == "agent"
    assert account["owner"] == "owner"


def test_agent_cannot_own_an_agent(service, sysop):
    active_user(service, sysop, "owner")
    active_user(service, sysop, "helper", kind="agent", owner="owner")
    with pytest.raises(HBBSError) as exc:
        signup(service, "helper2", kind="agent", owner="helper")
    assert exc.value.code == "invalid_owner"


def test_rejected_signup_cannot_login(service, sysop):
    result = signup(service, "mallory")
    service.resolve_queue(sysop, result["queue_id"], approve=False)
    with pytest.raises(HBBSError) as exc:
        service.login({"username": "mallory", "password": "a sufficiently long password"})
    assert exc.value.code == "account_rejected"


def test_login_failure_is_generic(service):
    with pytest.raises(HBBSError) as exc:
        service.login({"username": "nobody", "password": "whatever password"})
    assert exc.value.code == "invalid_credentials"
    assert "nobody" not in exc.value.message


def test_ban_revokes_tokens_and_unban_restores_login(service, sysop, human, clock):
    token = human["token"]
    assert service.authenticate(token) is not None
    banned = service.ban_account(sysop, human["account"]["id"], {"reason": "abuse"})
    assert banned["account"]["status"] == "banned"
    with pytest.raises(HBBSError) as exc:
        service.authenticate(token)
    assert exc.value.code == "account_banned"
    with pytest.raises(HBBSError) as exc:
        service.login({"username": "alice", "password": "a sufficiently long password"})
    assert exc.value.code == "account_banned"

    service.unban_account(sysop, human["account"]["id"])
    relogin = service.login({"username": "alice", "password": "a sufficiently long password"})
    assert relogin["token"]


def test_cannot_ban_self_or_sysop(service, sysop):
    with pytest.raises(HBBSError) as exc:
        service.ban_account(sysop, sysop["account"]["id"], {"reason": "oops"})
    assert exc.value.code == "cannot_ban_self"


def test_tokens_are_short_lived_and_logout_revokes(service, human, clock):
    token = human["token"]
    identity = service.authenticate(token)
    assert identity is not None
    service.logout(identity)
    assert service.authenticate(token) is None

    relogin = service.login({"username": "alice", "password": "a sufficiently long password"})
    clock.advance(service.config.token_ttl_seconds + 1)
    assert service.authenticate(relogin["token"]) is None


def test_only_sysop_can_read_account_list(service, sysop, human):
    listing = service.list_accounts(sysop, status="all")
    assert {account["username"] for account in listing["accounts"]} == {SYSOP, "alice"}
    with pytest.raises(HBBSError) as exc:
        service.list_accounts(human)
    assert exc.value.code == "sysop_required"
    assert SYSOP_PASSWORD not in repr(listing)
