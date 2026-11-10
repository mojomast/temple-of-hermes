"""In-memory sliding-window rate limits for HBBS/1.

Limits are per authenticated account. They are deliberately not persisted:
a restart gives every account a fresh window, which is the safer failure mode
for a small single-process BBS.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable

from .config import RateLimit
from .errors import rate_limited


class RateLimiter:
    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.time
        self._lock = threading.Lock()
        self._events: dict[tuple[int, str], deque[float]] = {}

    def check(self, account_id: int, action: str, limit: RateLimit) -> None:
        if limit.limit <= 0:
            raise rate_limited(limit.window_seconds, action=action)
        now = self._clock()
        cutoff = now - limit.window_seconds
        key = (int(account_id), action)
        with self._lock:
            events = self._events.setdefault(key, deque())
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit.limit:
                retry_after = max(1, int(events[0] + limit.window_seconds - now) + 1)
                raise rate_limited(retry_after, action=action)
            events.append(now)

    def peek(self, account_id: int, action: str, limit: RateLimit) -> int:
        """Return the number of events currently inside the window."""
        now = self._clock()
        cutoff = now - limit.window_seconds
        with self._lock:
            events = self._events.get((int(account_id), action))
            if not events:
                return 0
            while events and events[0] <= cutoff:
                events.popleft()
            return len(events)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
