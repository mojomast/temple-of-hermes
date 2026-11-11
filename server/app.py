"""Convenience helpers for embedding HBBS/1 in local tools and tests."""

from __future__ import annotations

from .hbbs.config import Config
from .hbbs.http import HBBSServer, make_server, start_background
from .hbbs.service import BOARDS, CONTRACT, HBBSService

__all__ = ["BOARDS", "CONTRACT", "Config", "HBBSServer", "HBBSService", "make_server", "start_background"]
