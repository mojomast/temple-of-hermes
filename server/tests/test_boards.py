from __future__ import annotations

import pytest

from hbbs.errors import HBBSError

from conftest import active_user, signup


def test_five_initial_boards(service):
    boards = service.list_boards()["boards"]
    assert [board["name"] for board in boards] == ["general", "agents", "holyc", "lore", "announcements"]
    titles = {board["name"]: board["title"] for board in boards}
    assert titles["general"] == "General chat"
    assert titles["agents"] == "Agent-to-agent"
    assert titles["holyc"] == "HolyC code share"
    assert titles["lore"] == "Nous lore"
    assert titles["announcements"] == "Announcements"
    assert next(board for board in boards if board["name"] == "announcements")["writable_by"] == "sysop"


def test_active_accounts_can_post_and_read(service, sysop, human):
    created = service.create_post(human, "general", {"subject": "Hello", "body": "First post."})
    assert created["status"] == "published"
    assert created["board"] == "general"
    assert created["untrusted"] is True

    listing = service.list_posts(None, "general")
    assert [post["subject"] for post in listing["posts"]] == ["Hello"]
    assert listing["posts"][0]["body"] == "First post."
    assert listing["next_before"] is None

    fetched = service.get_post(None, created["id"])
    assert fetched["post"]["id"] == created["id"]


def test_agents_may_post_to_agent_board(service, sysop):
    active_user(service, sysop, "alice")
    helper = active_user(service, sysop, "helper", kind="agent", owner="alice")
    post = service.create_post(helper, "agents", {"subject": "Ping", "body": "Any agents awake?"})
    assert post["author"]["kind"] == "agent"
    assert service.list_posts(None, "agents")["posts"][0]["body"] == "Any agents awake?"


def test_announcements_are_sysop_write_only(service, sysop, human):
    with pytest.raises(HBBSError) as exc:
        service.create_post(human, "announcements", {"subject": "Nope", "body": "nope"})
    assert exc.value.code == "board_read_only"

    created = service.create_post(sysop, "announcements", {"subject": "Welcome", "body": "The BBS is up."})
    assert created["status"] == "published"
    assert service.list_posts(None, "announcements")["posts"][0]["subject"] == "Welcome"


def test_unknown_board_and_validation(service, human):
    with pytest.raises(HBBSError) as exc:
        service.list_posts(None, "nope")
    assert exc.value.code == "unknown_board"

    with pytest.raises(HBBSError) as exc:
        service.create_post(human, "general", {"subject": "", "body": "x"})
    assert exc.value.code == "validation_error"

    with pytest.raises(HBBSError) as exc:
        service.create_post(human, "general", {"subject": "x" * 201, "body": "x"})
    assert exc.value.code == "validation_error"


def test_pagination_and_limits(service, human):
    for index in range(5):
        service.create_post(human, "lore", {"subject": f"Story {index}", "body": "body"})
    first = service.list_posts(None, "lore", limit=2)
    assert [post["subject"] for post in first["posts"]] == ["Story 4", "Story 3"]
    assert first["next_before"] == first["posts"][-1]["id"]
    second = service.list_posts(None, "lore", limit=2, before=first["next_before"])
    assert [post["subject"] for post in second["posts"]] == ["Story 2", "Story 1"]


def test_anonymous_can_read_but_not_post(service):
    with pytest.raises(HBBSError) as exc:
        service.create_post(None, "general", {"subject": "x", "body": "y"})
    assert exc.value.code == "unauthorized"
    assert service.list_posts(None, "general")["posts"] == []


def test_pending_author_can_read_own_post_but_public_cannot(service, sysop, monkeypatch):
    from dataclasses import replace

    service.config = replace(service.config, post_moderation=True)
    user = active_user(service, sysop, "bob")
    created = service.create_post(user, "general", {"subject": "Queued", "body": "wait"})
    assert created["status"] == "pending"
    assert service.list_posts(None, "general")["posts"] == []
    assert service.get_post(user, created["id"])["post"]["status"] == "pending"
    with pytest.raises(HBBSError) as exc:
        service.get_post(None, created["id"])
    assert exc.value.code == "post_not_found"
    assert service.get_post(sysop, created["id"])["post"]["status"] == "pending"
