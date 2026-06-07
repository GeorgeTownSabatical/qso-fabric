from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict


@dataclass
class TokenBucket:
    capacity: int
    refill_per_sec: float
    tokens: float
    updated_at: float


class RateLimiter:
    def __init__(self, capacity: int = 30, refill_per_sec: float = 15.0) -> None:
        now = time.monotonic()
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec
        self._buckets: DefaultDict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(capacity=capacity, refill_per_sec=refill_per_sec, tokens=float(capacity), updated_at=now)
        )

    def allow(self, key: str, cost: float = 1.0) -> bool:
        bucket = self._buckets[key]
        now = time.monotonic()
        elapsed = max(now - bucket.updated_at, 0.0)
        bucket.tokens = min(float(bucket.capacity), bucket.tokens + elapsed * bucket.refill_per_sec)
        bucket.updated_at = now

        if bucket.tokens < cost:
            return False

        bucket.tokens -= cost
        return True
