"""Run the HBBS/1 server: ``python -m hbbs``.

Bind address, TLS certificate/key, database path and bootstrap credentials all
come from the environment (see README.md). ``--check`` initializes the store
and exits without opening a socket.
"""

from __future__ import annotations

import argparse
import sys

from .config import Config
from .http import serve_forever
from .service import HBBSService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hbbs", description="Temple of Hermes HBBS/1 server")
    parser.add_argument("--check", action="store_true", help="validate configuration and storage, then exit")
    args = parser.parse_args(argv)
    try:
        config = Config.from_env()
        config.check_bind_safety()
        service = HBBSService(config)
    except Exception as exc:  # Config errors are operator-facing, never include secrets.
        print(f"hbbs: configuration error: {exc}", file=sys.stderr)
        return 2
    if args.check:
        print("hbbs: configuration and storage OK")
        return 0
    try:
        serve_forever(config)
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
