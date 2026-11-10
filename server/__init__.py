"""Repo-local HBBS/1 server package.

The implementation lives in :mod:`hbbs`. This wrapper makes
``from server.hbbs import BBS1Service`` and ``python -m server`` work when the
repository root is on ``PYTHONPATH``.
"""

from .hbbs import (
    BOARDS,
    CONTRACT,
    BBS1Connection,
    BBS1Error,
    BBS1Server,
    BBS1Service,
    Config,
    Frame,
    HBBSError,
    HBBSService,
    RateLimit,
    Session,
    encode_frame,
    make_server,
    read_frame,
    start_background,
)

__all__ = [
    "BOARDS",
    "CONTRACT",
    "BBS1Connection",
    "BBS1Error",
    "BBS1Server",
    "BBS1Service",
    "Config",
    "Frame",
    "HBBSError",
    "HBBSService",
    "RateLimit",
    "Session",
    "encode_frame",
    "make_server",
    "read_frame",
    "start_background",
]
