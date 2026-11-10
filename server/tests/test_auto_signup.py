from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from hbbs.bbs1 import BBS1Connection, BBS1Service
from hbbs.config import Config
from hbbs.errors import HBBSError
from hbbs.frames import Frame
from hbbs.service import HBBSService


class Clock:
    def __init__(self, start: int = 1_700_000_000) -> None:
        self.now = int(start)

    def __call__(self) -> float:
        return float(self.now)

    def advance(self, seconds: int) -> None:
        self.now += int(seconds)


def make_bbs1(tmp_path: Path, clock: Clock, *, db_name: str = "hbbs1.sqlite3", **overrides) -> BBS1Service:
    config = replace(Config(db_path=str(tmp_path / db_name)), **overrides)
    service = BBS1Service(config, clock=clock)
    service.bootstrap_sysop("sysop_ada", "Ada Sysop")
    service.create_account("ada_human", "Ada (human)")
    service.create_account("hermes_agent_7", "Hermes Agent 7", kind="agent", owner_account="ada_human")
    return service


def frame(command: str, args: dict, frame_id: str = "r-1") -> Frame:
    body = {"v": 1, "command": command, "args": args}
    return Frame("REQ", frame_id, command, 0, body, b"")


def auth(service: BBS1Service, args: dict, *, peer: str | None = None):
    connection = BBS1Connection(service, peer=peer)
    return connection.handle(frame("AUTH", args))


def signup_args(account: str, kind: str = "human", *, owner: str | None = None) -> dict:
    args = {
        "action": "signup",
        "account": account,
        "display_name": f"Display {account}",
        "kind": kind,
    }
    if owner is not None:
        args["owner_account"] = owner
    return args


def test_auto_human_is_approved_with_tokens_and_whoami(tmp_path):
    clock = Clock()
    service = make_bbs1(tmp_path, clock, signup_mode="auto")

    response, close = auth(service, signup_args("auto_human_1"))
    assert response["ok"] is True, response
    assert close is False
    data = response["data"]
    assert data["grant"] == "signup"
    assert data["application"]["status"] == "approved"
    assert data["application"]["queue_position"] == 0
    assert data["account"]["account"] == "auto_human_1"
    assert data["account"]["role"] == "human"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["session"]["session_id"]

    approvals = [entry for entry in service.list_audit()["entries"] if entry["action"] == "account.approve"]
    assert approvals
    assert approvals[0]["actor"] == "system:auto"
    audit_blob = json.dumps(service.list_audit())
    assert "Display auto_human_1" not in audit_blob
    assert data["access_token"] not in audit_blob
    assert data["refresh_token"] not in audit_blob

    connection = BBS1Connection(service)
    login, close = connection.handle(frame("AUTH", {"action": "login", "token": data["access_token"]}))
    assert login["ok"] is True, login
    assert close is False
    whoami, _ = connection.handle(frame("WHOAMI", {}))
    assert whoami["ok"] is True, whoami
    assert whoami["data"]["account"]["account"] == "auto_human_1"


def test_auto_agent_with_approved_owner_is_approved(tmp_path):
    clock = Clock()
    service = make_bbs1(tmp_path, clock, signup_mode="auto")

    response, close = auth(service, signup_args("auto_agent_1", "agent", owner="ada_human"))
    assert response["ok"] is True, response
    assert close is False
    data = response["data"]
    assert data["grant"] == "signup"
    assert data["application"]["status"] == "approved"
    assert data["application"]["owner_account"] == "ada_human"
    assert data["account"]["kind"] == "agent"
    assert data["account"]["role"] == "agent"
    assert data["account"]["owner_account"] == "ada_human"
    assert data["access_token"]
    assert data["refresh_token"]


def test_auto_agent_without_eligible_owner_goes_pending(tmp_path):
    clock = Clock()
    service = make_bbs1(tmp_path, clock, signup_mode="auto")

    missing, close = auth(service, signup_args("auto_agent_2", "agent"))
    assert missing["ok"] is True, missing
    assert close is True
    assert missing["data"]["application"]["status"] == "pending_moderation"
    assert "access_token" not in json.dumps(missing)

    ineligible, close = auth(service, signup_args("auto_agent_3", "agent", owner="hermes_agent_7"))
    assert ineligible["ok"] is True, ineligible
    assert close is True
    assert ineligible["data"]["application"]["status"] == "pending_moderation"
    assert "access_token" not in json.dumps(ineligible)


def test_auto_approve_kinds_filter(tmp_path):
    clock = Clock()
    service = make_bbs1(
        tmp_path,
        clock,
        signup_mode="auto",
        auto_approve_kinds=("human",),
    )

    human, _ = auth(service, signup_args("filter_human"))
    assert human["ok"] is True, human
    assert human["data"]["application"]["status"] == "approved"
    assert human["data"]["access_token"]

    agent, _ = auth(service, signup_args("filter_agent", "agent", owner="ada_human"))
    assert agent["ok"] is True, agent
    assert agent["data"]["application"]["status"] == "pending_moderation"
    assert "access_token" not in json.dumps(agent)


def test_auto_approve_kinds_can_select_only_agents(tmp_path):
    clock = Clock()
    service = make_bbs1(
        tmp_path,
        clock,
        signup_mode="auto",
        auto_approve_kinds=("agent",),
    )

    agent, _ = auth(service, signup_args("selected_agent", "agent", owner="ada_human"))
    assert agent["ok"] is True, agent
    assert agent["data"]["application"]["status"] == "approved"
    assert agent["data"]["access_token"]

    human, _ = auth(service, signup_args("unselected_human"))
    assert human["ok"] is True, human
    assert human["data"]["application"]["status"] == "pending_moderation"
    assert "access_token" not in json.dumps(human)


def test_auto_mode_refuses_banned_account(tmp_path):
    clock = Clock()
    service = make_bbs1(tmp_path, clock, signup_mode="auto")
    service.ban_account("ada_human", actor="sysop_ada")

    response, close = auth(service, signup_args("ada_human"))
    assert response["ok"] is False, response
    assert response["error"]["code"] == "account_banned"
    assert close is True
    with service.db.connect() as conn:
        assert service._account(conn, "ada_human")["status"] == "banned"


def test_auto_mode_auth_rate_limit_still_applies(tmp_path):
    clock = Clock()
    service = make_bbs1(tmp_path, clock, signup_mode="auto")

    for index in range(5):
        response, _ = auth(service, signup_args(f"rate_human_{index}"), peer="peer-rate")
        assert response["ok"] is True, response
        assert response["data"]["application"]["status"] == "approved"

    limited, close = auth(service, signup_args("rate_human_5"), peer="peer-rate")
    assert limited["ok"] is False, limited
    assert limited["error"]["code"] == "rate_limited"
    assert close is True


def test_open_mode_still_goes_pending(tmp_path):
    clock = Clock()
    service = make_bbs1(tmp_path, clock, signup_mode="open")

    response, close = auth(service, signup_args("open_human"))
    assert response["ok"] is True, response
    assert close is True
    assert response["data"]["application"]["status"] == "pending_moderation"
    assert "access_token" not in json.dumps(response)
    assert "refresh_token" not in json.dumps(response)


def test_closed_mode_still_refuses_signup(tmp_path):
    clock = Clock()
    service = make_bbs1(tmp_path, clock, signup_mode="closed")

    response, close = auth(service, signup_args("closed_human"))
    assert response["ok"] is False, response
    assert response["error"]["code"] == "forbidden"
    assert response["error"]["field"] == "args.account"
    assert close is True


def test_service_auto_signup_approves_humans_and_eligible_agents(tmp_path):
    clock = Clock()
    config = replace(
        Config(
            db_path=str(tmp_path / "service.sqlite3"),
            sysop_username="root",
            sysop_password="correct horse battery staple",
        ),
        signup_mode="auto",
    )
    service = HBBSService(config, clock=clock)

    human = service.signup(
        {"username": "service_human", "display_name": "Service Human", "password": "a sufficiently long password"}
    )
    assert human["status"] == "active"
    assert human["account"]["status"] == "active"
    assert "queue_id" in human
    assert service.login({"username": "service_human", "password": "a sufficiently long password"})["token"]

    agent = service.signup(
        {
            "username": "service_agent",
            "display_name": "Service Agent",
            "kind": "agent",
            "owner": "service_human",
            "password": "a sufficiently long password",
        }
    )
    assert agent["status"] == "active"
    assert agent["account"]["kind"] == "agent"
    assert agent["account"]["owner"] == "service_human"

    no_owner = service.signup(
        {
            "username": "service_agent_2",
            "display_name": "Service Agent 2",
            "kind": "agent",
            "password": "a sufficiently long password",
        }
    )
    assert no_owner["status"] == "pending"
    assert no_owner["account"]["status"] == "pending"

    with service.db.connect() as conn:
        approvals = conn.execute(
            "SELECT * FROM audit WHERE action = 'account.approve' ORDER BY id"
        ).fetchall()
    assert approvals
    assert all(json.loads(row["detail"]).get("actor") == "system:auto" for row in approvals)

    sysop = service.login({"username": "root", "password": "correct horse battery staple"})
    audit_entries = service.list_audit(sysop, limit=500)["entries"]
    auto_approvals = [entry for entry in audit_entries if entry["action"] == "account.approve"]
    assert auto_approvals
    assert all(entry["actor"] == "system:auto" for entry in auto_approvals)


def test_service_auto_mode_refuses_banned_account(tmp_path):
    clock = Clock()
    config = replace(
        Config(
            db_path=str(tmp_path / "service_banned.sqlite3"),
            sysop_username="root",
            sysop_password="correct horse battery staple",
        ),
        signup_mode="auto",
    )
    service = HBBSService(config, clock=clock)
    human = service.signup(
        {"username": "banned_human", "display_name": "Banned Human", "password": "a sufficiently long password"}
    )
    sysop = service.login({"username": "root", "password": "correct horse battery staple"})
    service.ban_account(sysop, human["account"]["id"], {"reason": "test ban"})

    with pytest.raises(HBBSError) as exc:
        service.signup(
            {"username": "banned_human", "display_name": "Banned Human", "password": "a sufficiently long password"}
        )
    assert exc.value.code == "account_banned"
