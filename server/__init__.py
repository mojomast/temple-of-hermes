"""Repo-local HBBS/1 server package.

The implementation lives in :mod:`hbbs`. This wrapper makes
``from server.hbbs import HBBSService`` and ``python -m server`` work when the
repository root is on ``PYTHONPATH``.
"""

from .hbbs import BOARDS, CONTRACT, Config, HBBSError, HBBSService, RateLimit

__all__ = ["BOARDS", "CONTRACT", "Config", "HBBSError", "HBBSService", "RateLimit"]
