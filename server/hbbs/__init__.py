"""HBBS/1 — the Temple of Hermes bulletin-board server."""

from .bbs1 import BOARDS as HBBS1_BOARDS
from .bbs1 import BBS1Connection, BBS1Service, Session
from .config import Config, RateLimit
from .errors import BBS1Error, HBBSError
from .frames import Frame, encode_frame, read_frame
from .server import BBS1Server, make_server, start_background
from .service import BOARDS, CONTRACT, HBBSService

__all__ = [
    "BOARDS",
    "CONTRACT",
    "BBS1Connection",
    "BBS1Error",
    "BBS1Server",
    "BBS1Service",
    "Config",
    "Frame",
    "HBBS1_BOARDS",
    "HBBSError",
    "HBBSService",
    "RateLimit",
    "Session",
    "encode_frame",
    "make_server",
    "read_frame",
    "start_background",
]
__version__ = "1.0.0"
