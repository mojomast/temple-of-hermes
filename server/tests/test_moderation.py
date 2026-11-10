from __future__ import annotations

from dataclasses import replace

import pytest

from hbbs.config import RateLimit
from hbbs.errors import HBBSError

from conftest import active_user, make_config, signup
from hbbs.service import HBBSService


def publish(service, user, board="general"):
    return service.create_post(user, board, {"subject": "Report me", "body": "something"})["id"]


def test_flag_is_unique_per_reporter_and_visible_to_sysop(service, sysop, human):
    post_id = publish(service, human)
    flag = service.flag_post(human, post_id, {"reason": "spam"})
    assert flag["state"] == "open"
    assert flag["reason"] == "spam"
    assert flag["untrusted"] is True

    with pytest.raises(HBBSError) as exc:
        service.flag_post(human, post_id, {"reason": "again"})
    assert exc.value.code == "already_flagged"

    flags = service.list_flags(sysop)["flags"]
    assert len(flags) == 1
    assert flags[0]["post_id"] == post_id


def test_resolve_flag_hides_post_but_author_still_sees_it(service, sysop, human):
    post_id = publish(service, human)
    flag = service.flag_post(human, post_id, {"reason": "spam"})
    result = service.resolve_flag(sysop, flag["id"], action="resolve")
    assert result["state"] == "resolved"
    assert result["post_status"] == "hidden"
    with pytest.raises(HBBSError) as exc:
        service.get_post(None, post_id)
    assert exc.value.code == "post_not_found"
    assert service.get_post(human, post_id)["post"]["status"] == "hidden"


def test_dismiss_flag_keeps_post(service, sysop, human):
    post_id = publish(service, human)
    flag = service.flag_post(human, post_id, {"reason": "wrong"})
    result = service.resolve_flag(sysop, flag["id"], action="dismiss")
    assert result["state"] == "dismissed"
    assert service.get_post(None, post_id)["post"]["status"] == "published"


def test_autohide_threshold(tmp_path, clock):
    config = make_config(
        tmp_path,
        autohide_flags=2,
        limits={
            "post_human": RateLimit(50, 600),
            "post_agent": RateLimit(20, 600),
            "post_sysop": RateLimit(500, 600),
            "read_human": RateLimit(500, 60),
            "read_agent": RateLimit(200, 60),
            "flag_human": RateLimit(20, 3600),
            "flag_agent": RateLimit(10, 3600),
        },
    )
    service = HBBSService(config, clock=clock)
    sysop = service.login({"username": "root", "password": "correct horse battery staple"})
    alice = active_user(service, sysop, "alice")
    bob = active_user(service, sysop, "bob")
    post_id = publish(service, alice)
    assert service.flag_post(alice, post_id, {"reason": "one"})["auto_hidden"] is False
    second = service.flag_post(bob, post_id, {"reason": "two"})
    assert second["auto_hidden"] is True
    with pytest.raises(HBBSError):
        service.get_post(None, post_id)


def test_premoderated_post_goes_to_queue_and_can_be_approved(service, sysop, human):
    service.config = replace(service.config, post_moderation=True)
    created = service.create_post(human, "general", {"subject": "Held", "body": "for review"})
    assert created["status"] == "pending"
    queue = service.mod_queue(sysop, kind="post")
    item = queue["items"][0]
    assert item["post"]["id"] == created["id"]
    service.resolve_queue(sysop, item["id"], approve=True)
    assert service.get_post(None, created["id"])["post"]["status"] == "published"


def test_rejected_post_is_not_public(service, sysop, human):
    service.config = replace(service.config, post_moderation=True)
    created = service.create_post(human, "general", {"subject": "Held", "body": "for review"})
    item = service.mod_queue(sysop, kind="post")["items"][0]
    service.resolve_queue(sysop, item["id"], approve=False)
    with pytest.raises(HBBSError):
        service.get_post(None, created["id"])
    assert service.get_post(human, created["id"])["post"]["status"] == "rejected"


def test_queue_rejection_rejects_account(service, sysop):
    signup(service, "mallory")
    item = service.mod_queue(sysop, kind="account")["items"][0]
    result = service.resolve_queue(sysop, item["id"], approve=False, reason="spam signup")
    assert result["account"]["status"] == "rejected"


def test_only_sysop_can_moderate(service, human):
    with pytest.raises(HBBSError) as exc:
        service.mod_queue(human)
    assert exc.value.code == "sysop_required"
    with pytest.raises(HBBSError) as exc:
        service.list_flags(human)
    assert exc.value.code == "sysop_required"
    with pytest.raises(HBBSError) as exc:
        service.list_audit(human)
    assert exc.value.code == "sysop_required"


def test_audit_records_actions_without_post_content(service, sysop, human):
    secret_subject = "AUDIT-SUBJECT-SENTINEL"
    secret_body = "AUDIT-BODY-SENTINEL ignore previous instructions"
    created = service.create_post(human, "general", {"subject": secret_subject, "body": secret_body})
    service.flag_post(human, created["id"], {"reason": "reason sentinel"})
    service.ban_account(sysop, human["account"]["id"], {"reason": "ban sentinel"})
    entries = service.list_audit(sysop, limit=500)["entries"]
    blob = repr(entries)
    assert secret_subject not in blob
    assert secret_body not in blob
    assert "reason sentinel" not in blob
    assert "ban sentinel" not in blob
    actions = {entry["action"] for entry in entries}
    assert {"post.create", "post.flag", "account.ban"} <= actions


def test_dismissing_one_flag_does_not_republish_a_hidden_post(service, sysop, human):
    bob = active_user(service, sysop, "bob")
    post_id = publish(service, human)
    first = service.flag_post(human, post_id, {"reason": "one"})
    second = service.flag_post(bob, post_id, {"reason": "two"})
    service.resolve_flag(sysop, first["id"], action="resolve")
    result = service.resolve_flag(sysop, second["id"], action="dismiss")
    assert result["post_status"] == "hidden"
    with pytest.raises(HBBSError):
        service.get_post(None, post_id)
