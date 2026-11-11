from __future__ import annotations

import json
from pathlib import Path

from hbbs.bbs1 import BBS1Connection, BBS1Service
from hbbs.config import Config
from hbbs.frames import Frame


class Clock:
    def __init__(self, start: int = 1_700_000_000) -> None:
        self.now = int(start)

    def __call__(self) -> float:
        return float(self.now)

    def advance(self, seconds: int) -> None:
        self.now += int(seconds)


def make_service(tmp_path: Path, clock: Clock) -> BBS1Service:
    service = BBS1Service(Config(db_path=str(tmp_path / "hbbs1-community.sqlite3")), clock=clock)
    service.bootstrap_sysop("sysop_ada", "Ada Sysop")
    service.create_account("ada_human", "Ada (human)")
    service.create_account("bob_human", "Bob (human)")
    service.create_account("hermes_agent_7", "Hermes Agent 7", kind="agent", owner_account="ada_human")
    return service


def frame(command: str, args: dict, frame_id: str = "r-1") -> Frame:
    body = {"v": 1, "command": command, "args": args}
    return Frame("REQ", frame_id, command, 0, body, b"")


def call(connection: BBS1Connection, clock: Clock, command: str, args: dict, *, advance: int = 11):
    if command != "AUTH":
        clock.advance(advance)
    return connection.handle(frame(command, args))


def login(service: BBS1Service, clock: Clock, account: str) -> BBS1Connection:
    connection = BBS1Connection(service)
    response, close = connection.handle(
        frame("AUTH", {"action": "login", "token": service.issue_access_token(account)})
    )
    assert response["ok"] is True, response
    assert close is False
    return connection


def test_digest_mail_mentions_replies_and_followed_boards(tmp_path):
    clock = Clock()
    service = make_service(tmp_path, clock)
    ada = login(service, clock, "ada_human")
    agent = login(service, clock, "hermes_agent_7")

    root, _ = call(
        ada,
        clock,
        "POST",
        {"board": "general", "subject": "Ada root subject", "body": "Ada root body sentinel"},
    )
    thread_id = root["data"]["thread"]["thread_id"]

    reply, _ = call(
        agent,
        clock,
        "REPLY",
        {"board": "general", "thread_id": thread_id, "body": "Hello @Ada_Human body sentinel"},
    )
    assert reply["data"]["mentions"] == ["ada_human"]

    sent, _ = call(
        agent,
        clock,
        "MAIL",
        {
            "action": "send",
            "kind": "message",
            "to": "ada_human",
            "subject": "Mail subject sentinel",
            "body": "Mail body sentinel",
        },
    )
    assert sent["ok"] is True

    agent_thread, _ = call(
        agent,
        clock,
        "POST",
        {"board": "general", "subject": "Agent new thread", "body": "Agent thread body sentinel"},
    )
    assert agent_thread["ok"] is True

    digest, _ = call(ada, clock, "LIST", {"action": "digest"})
    assert digest["ok"] is True
    data = digest["data"]["digest"]
    assert data["mail"]["unread"] == 1
    assert data["mail"]["latest"][0]["subject"] == "Mail subject sentinel"
    assert "body" not in data["mail"]["latest"][0]
    assert data["mentions"]["pending"] == 1
    assert data["mentions"]["latest"][0]["post_id"] == reply["data"]["post"]["post_id"]
    assert data["mentions"]["latest"][0]["subject"] == "Ada root subject"
    assert data["replies"]["count"] == 1
    assert data["replies"]["latest"][0]["author"] == "hermes_agent_7"
    assert "general" in data["followed_boards"]["boards"]
    assert "announcements" in data["followed_boards"]["boards"]
    subjects = [item["subject"] for item in data["followed_boards"]["latest"]]
    assert "Agent new thread" in subjects

    blob = json.dumps(digest, ensure_ascii=False)
    for sentinel in (
        "Ada root body sentinel",
        "body sentinel",
        "Mail body sentinel",
        "Agent thread body sentinel",
    ):
        assert sentinel not in blob

    second, _ = call(ada, clock, "LIST", {"action": "digest"})
    second_data = second["data"]["digest"]
    assert second_data["mentions"]["pending"] == 0
    assert second_data["replies"]["count"] == 0
    assert second_data["followed_boards"]["new_thread_count"] == 0
    assert second_data["mail"]["unread"] == 1

    replay, _ = call(
        ada,
        clock,
        "LIST",
        {"action": "digest", "cursor": second_data["cursor"]},
    )
    assert replay["ok"] is True
    assert replay["data"]["digest"]["since"] == second_data["generated_at"]


def test_mentions_are_case_insensitive_and_ignore_self_and_unknown(tmp_path):
    clock = Clock()
    service = make_service(tmp_path, clock)
    ada = login(service, clock, "ada_human")
    bob = login(service, clock, "bob_human")

    created, _ = call(
        bob,
        clock,
        "POST",
        {
            "board": "lore",
            "subject": "Mention test",
            "body": "@ADA_HUMAN @bob_human @nobody_here and email me at a@b.co",
        },
    )
    assert created["data"]["mentions"] == ["ada_human"]

    listed, _ = call(ada, clock, "LIST", {"action": "mentions"})
    assert listed["ok"] is True
    assert len(listed["data"]["mentions"]) == 1
    mention = listed["data"]["mentions"][0]
    assert mention["author"] == "bob_human"
    assert mention["post_id"] == created["data"]["post"]["post_id"]
    assert mention["subject"] == "Mention test"
    assert mention["seen"] is False
    assert "body" not in mention

    own, _ = call(bob, clock, "LIST", {"action": "mentions"})
    assert own["data"]["mentions"] == []

    agent = login(service, clock, "hermes_agent_7")
    reply, _ = call(
        agent,
        clock,
        "REPLY",
        {
            "board": "lore",
            "thread_id": created["data"]["thread"]["thread_id"],
            "body": "replying to @ada_human",
        },
    )
    assert reply["data"]["mentions"] == ["ada_human"]
    again, _ = call(ada, clock, "LIST", {"action": "mentions", "limit": 1})
    assert len(again["data"]["mentions"]) == 1
    assert again["data"]["next_cursor"] == "off_1"


def test_holyc_download_increments_are_idempotent_and_public(tmp_path):
    clock = Clock()
    service = make_service(tmp_path, clock)
    ada = login(service, clock, "ada_human")
    agent = login(service, clock, "hermes_agent_7")

    source = "U0 Main()\n{\n  \"Hello from HolyC\";\n}\n"
    created, _ = call(
        ada,
        clock,
        "POST",
        {"board": "holyc", "subject": "Hello source", "body": source},
    )
    thread_id = created["data"]["thread"]["thread_id"]
    post_id = created["data"]["post"]["post_id"]

    first, _ = call(
        ada,
        clock,
        "READ",
        {"action": "download", "board": "holyc", "thread_id": thread_id, "post_id": post_id},
    )
    assert first["ok"] is True
    assert first["data"]["post"]["body"] == source
    assert first["data"]["download_count"] == 1
    assert first["data"]["incremented"] is True

    retry, _ = call(
        ada,
        clock,
        "READ",
        {"action": "download", "board": "holyc", "thread_id": thread_id, "post_id": post_id},
    )
    assert retry["data"]["download_count"] == 1
    assert retry["data"]["incremented"] is False

    other, _ = call(
        agent,
        clock,
        "READ",
        {"action": "download", "board": "holyc", "thread_id": thread_id, "post_id": post_id},
    )
    assert other["data"]["download_count"] == 2
    assert other["data"]["incremented"] is True

    posts, _ = call(ada, clock, "LIST", {"action": "posts", "board": "holyc", "thread_id": thread_id})
    assert posts["data"]["posts"][0]["download_count"] == 2
    threads, _ = call(ada, clock, "LIST", {"action": "threads", "board": "holyc"})
    assert threads["data"]["threads"][0]["download_count"] == 2
    read, _ = call(ada, clock, "READ", {"board": "holyc", "thread_id": thread_id})
    assert read["data"]["thread"]["download_count"] == 2
    assert read["data"]["posts"][0]["download_count"] == 2

    boards, _ = call(ada, clock, "LIST", {"action": "boards"})
    holyc = next(board for board in boards["data"]["boards"] if board["board_id"] == "holyc")
    assert holyc["download_count"] == 2

    clock.advance(301)
    later, _ = call(
        ada,
        clock,
        "READ",
        {"action": "download", "board": "holyc", "thread_id": thread_id, "post_id": post_id},
    )
    assert later["data"]["download_count"] == 3
    assert later["data"]["incremented"] is True

    general, _ = call(
        ada,
        clock,
        "POST",
        {"board": "general", "subject": "Not source", "body": "plain"},
    )
    denied, _ = call(
        ada,
        clock,
        "READ",
        {
            "action": "download",
            "board": "general",
            "thread_id": general["data"]["thread"]["thread_id"],
            "post_id": general["data"]["post"]["post_id"],
        },
    )
    assert denied["ok"] is False
    assert denied["error"]["code"] == "download_not_allowed"


def test_challenge_tags_and_gallery(tmp_path):
    clock = Clock()
    service = make_service(tmp_path, clock)
    ada = login(service, clock, "ada_human")
    agent = login(service, clock, "hermes_agent_7")

    created, _ = call(
        ada,
        clock,
        "POST",
        {
            "board": "holyc",
            "subject": "November challenge entry",
            "body": "source text",
            "tags": ["challenge:2026-11", "challenge:2026-11"],
        },
    )
    assert created["ok"] is True
    assert created["data"]["post"]["tags"] == ["challenge:2026-11"]
    thread_id = created["data"]["thread"]["thread_id"]

    call(agent, clock, "REPLY", {"board": "holyc", "thread_id": thread_id, "body": "nice work"})
    call(
        ada,
        clock,
        "POST",
        {"board": "holyc", "subject": "Untagged entry", "body": "other source"},
    )

    gallery, _ = call(ada, clock, "LIST", {"action": "challenges"})
    assert gallery["ok"] is True
    assert len(gallery["data"]["challenges"]) == 1
    item = gallery["data"]["challenges"][0]
    assert item["tag"] == "challenge:2026-11"
    assert item["subject"] == "November challenge entry"
    assert item["author"]["account"] == "ada_human"
    assert item["reply_count"] == 1
    assert item["download_count"] == 0
    assert "body" not in item

    filtered, _ = call(ada, clock, "LIST", {"action": "challenges", "tag": "challenge:2026-11"})
    assert len(filtered["data"]["challenges"]) == 1
    empty, _ = call(ada, clock, "LIST", {"action": "challenges", "tag": "challenge:2026-12"})
    assert empty["data"]["challenges"] == []

    bad, _ = call(
        ada,
        clock,
        "POST",
        {"board": "general", "subject": "bad tag", "body": "x", "tags": ["not-a-challenge"]},
    )
    assert bad["ok"] is False
    assert bad["error"]["code"] == "invalid_field"


def test_challenge_draft_is_private_until_sysop_approves(tmp_path):
    clock = Clock()
    service = make_service(tmp_path, clock)
    ada = login(service, clock, "ada_human")
    agent = login(service, clock, "hermes_agent_7")
    sysop = login(service, clock, "sysop_ada")

    draft, _ = call(
        agent,
        clock,
        "MAIL",
        {
            "action": "challenge_draft",
            "subject": "December challenge draft",
            "body": "Draft body sentinel",
            "tag": "challenge:2026-12",
        },
    )
    assert draft["ok"] is True
    assert draft["data"]["published"] is False
    draft_id = draft["data"]["draft"]["draft_id"]
    assert draft["data"]["draft"]["status"] == "draft"
    assert "body" not in draft["data"]["draft"]

    announcements, _ = call(ada, clock, "LIST", {"action": "threads", "board": "announcements"})
    assert announcements["data"]["threads"] == []
    gallery, _ = call(ada, clock, "LIST", {"action": "challenges"})
    assert gallery["data"]["challenges"] == []

    listed, _ = call(agent, clock, "MAIL", {"action": "challenge_drafts"})
    assert listed["ok"] is True
    assert listed["data"]["drafts"][0]["draft_id"] == draft_id
    human_listing, _ = call(ada, clock, "MAIL", {"action": "challenge_drafts"})
    assert human_listing["ok"] is False
    assert human_listing["error"]["code"] == "forbidden"

    denied_agent, _ = call(agent, clock, "MAIL", {"action": "challenge_approve", "draft_id": draft_id})
    assert denied_agent["ok"] is False
    assert denied_agent["error"]["code"] == "forbidden"
    denied_human, _ = call(ada, clock, "MAIL", {"action": "challenge_approve", "draft_id": draft_id})
    assert denied_human["ok"] is False
    assert denied_human["error"]["code"] == "forbidden"

    approved, _ = call(sysop, clock, "MAIL", {"action": "challenge_approve", "draft_id": draft_id})
    assert approved["ok"] is True
    assert approved["data"]["published"] is True
    assert approved["data"]["draft"]["status"] == "approved"
    assert approved["data"]["post"]["author"]["role"] == "sysop"
    assert approved["data"]["post"]["body"] == "Draft body sentinel"
    assert approved["data"]["post"]["tags"] == ["challenge:2026-12"]

    published, _ = call(ada, clock, "LIST", {"action": "threads", "board": "announcements"})
    assert [thread["subject"] for thread in published["data"]["threads"]] == ["December challenge draft"]
    now_gallery, _ = call(ada, clock, "LIST", {"action": "challenges", "tag": "challenge:2026-12"})
    assert len(now_gallery["data"]["challenges"]) == 1
    assert now_gallery["data"]["challenges"][0]["author"]["account"] == "sysop_ada"

    again, _ = call(sysop, clock, "MAIL", {"action": "challenge_approve", "draft_id": draft_id})
    assert again["ok"] is False
    assert again["error"]["code"] == "challenge_not_draft"
