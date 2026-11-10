"""Run the HBBS/1 server: ``python -m hbbs``.

The default transport is the HBBS/1 framed TCP/TLS protocol. Bind address,
TLS certificate/key, database path and optional bootstrap sysop account all
come from the environment (see README.md). ``--check`` initializes storage and
exits without opening a socket. ``--http`` runs the legacy JSON/HTTP adapter
for local tools; the contract transport is the frame server.
"""

from __future__ import annotations

import argparse
import sys

from .bbs1 import BBS1Service
from .config import Config
from .server import serve_forever as serve_frames


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hbbs", description="Temple of Hermes HBBS/1 server")
    parser.add_argument("--check", action="store_true", help="validate configuration and storage, then exit")
    parser.add_argument(
        "--transport",
        choices=("frames", "http"),
        default="frames",
        help="frames (HBBS/1, default) or the legacy local HTTP adapter",
    )
    args = parser.parse_args(argv)
    try:
        config = Config.from_env()
        config.check_bind_safety()
        service = BBS1Service(config)
    except Exception as exc:  # Config errors are operator-facing, never include secrets.
        print(f"hbbs: configuration error: {exc}", file=sys.stderr)
        return 2
    if args.check:
        print("hbbs: configuration and storage OK")
        return 0
    try:
        if args.transport == "http":
            from .http import serve_forever as serve_http

            serve_http(config)
        else:
            serve_frames(config, service)
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
