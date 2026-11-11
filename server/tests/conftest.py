from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hbbs.config import Config, RateLimit  # noqa: E402
from hbbs.service import HBBSService  # noqa: E402

SYSOP = "root"
SYSOP_PASSWORD = "correct horse battery staple"


class FakeClock:
    def __init__(self, start: int = 1_700_000_000) -> None:
        self.now = int(start)

    def __call__(self) -> float:
        return float(self.now)

    def advance(self, seconds: int) -> None:
        self.now += int(seconds)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def make_config(tmp_path: Path, **overrides) -> Config:
    base = Config(
        db_path=str(tmp_path / "hbbs.sqlite3"),
        # These suites exercise the moderated queue; auto is the server default.
        signup_mode="open",
        sysop_username=SYSOP,
        sysop_password=SYSOP_PASSWORD,
        token_ttl_seconds=900,
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
    return replace(base, **overrides)


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return make_config(tmp_path)


@pytest.fixture
def service(config: Config, clock: FakeClock) -> HBBSService:
    return HBBSService(config, clock=clock)


@pytest.fixture
def sysop(service: HBBSService) -> dict:
    return service.login({"username": SYSOP, "password": SYSOP_PASSWORD})


def signup(service: HBBSService, username: str, *, kind: str = "human", owner: str | None = None,
           password: str = "a sufficiently long password", display_name: str | None = None) -> dict:
    payload = {
        "username": username,
        "password": password,
        "kind": kind,
        "display_name": display_name or username,
    }
    if owner is not None:
        payload["owner"] = owner
    return service.signup(payload)


def approve(service: HBBSService, sysop_token: dict, username: str) -> dict:
    queue = service.mod_queue(sysop_token, kind="account")["items"]
    for item in queue:
        if item["account"] and item["account"]["username"] == username:
            return service.resolve_queue(sysop_token, item["id"], approve=True)
    raise AssertionError(f"no queue item for {username}")


def active_user(service: HBBSService, sysop_token: dict, username: str, *, kind: str = "human",
                owner: str | None = None, password: str = "a sufficiently long password") -> dict:
    signup(service, username, kind=kind, owner=owner, password=password)
    approve(service, sysop_token, username)
    return service.login({"username": username, "password": password})


@pytest.fixture
def human(service: HBBSService, sysop: dict) -> dict:
    return active_user(service, sysop, "alice")
