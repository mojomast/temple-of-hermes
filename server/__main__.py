"""Allow ``python -m server`` from the repository root."""

from .hbbs.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
