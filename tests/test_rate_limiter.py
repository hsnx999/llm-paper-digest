import pytest
from core.rate_limiter import RateLimiter, estimate_tokens, rate_limiter


class TestRateLimiter:
    def test_singleton(self):
        """All RateLimiter() calls return the same instance."""
        r1 = RateLimiter()
        r2 = RateLimiter()
        assert r1 is r2

    def test_module_instance_is_singleton(self):
        assert rate_limiter is RateLimiter()

    def test_estimate_tokens_non_empty(self):
        assert estimate_tokens("hello world") > 0

    def test_estimate_tokens_empty(self):
        assert estimate_tokens("") == 1  # len("") // 4 + 1

    @pytest.mark.asyncio
    async def test_acquire_allows_normal_usage(self):
        rl = RateLimiter()
        await rl.acquire(estimated_tokens=100)
        assert len(rl._req_times) == 1
