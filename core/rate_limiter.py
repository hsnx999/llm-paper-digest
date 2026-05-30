from __future__ import annotations

import asyncio
import time
from collections import deque

from loguru import logger


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return len(text) // 4 + 1


class RateLimiter:
    """Sliding-window rate limiter enforcing Groq free-tier limits:
    30 requests/minute, 12,000 tokens/minute.
    """

    MAX_REQUESTS = 30
    MAX_TOKENS = 12_000
    WINDOW = 60  # seconds

    _instance: RateLimiter | None = None

    def __new__(cls) -> RateLimiter:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._req_times: deque[float] = deque()
            cls._instance._tok_log: deque[tuple[float, int]] = deque()
        return cls._instance

    def __init__(self) -> None:
        pass

    def _clean(self, cutoff: float) -> None:
        while self._req_times and self._req_times[0] < cutoff:
            self._req_times.popleft()
        while self._tok_log and self._tok_log[0][0] < cutoff:
            self._tok_log.popleft()

    async def acquire(self, estimated_tokens: int = 0) -> None:
        now = time.monotonic()
        cutoff = now - self.WINDOW
        self._clean(cutoff)

        while len(self._req_times) >= self.MAX_REQUESTS:
            wait = self._req_times[0] + self.WINDOW - time.monotonic()
            if wait > 0:
                logger.info(f"Rate limit: waiting {wait:.1f}s for request slot")
                await asyncio.sleep(wait)
            self._clean(time.monotonic() - self.WINDOW)

        while estimated_tokens > 0:
            self._clean(time.monotonic() - self.WINDOW)
            used = sum(t for _, t in self._tok_log)
            if used + estimated_tokens <= self.MAX_TOKENS:
                break
            if self._tok_log:
                wait = self._tok_log[0][0] + self.WINDOW - time.monotonic()
                if wait > 0:
                    logger.info(f"Rate limit: waiting {wait:.1f}s for token budget")
                    await asyncio.sleep(wait)

        now = time.monotonic()
        self._req_times.append(now)
        if estimated_tokens > 0:
            self._tok_log.append((now, estimated_tokens))


rate_limiter = RateLimiter()
