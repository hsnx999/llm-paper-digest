import pytest
from core.rate_limiter import RateLimiter, estimate_tokens, rate_limiter


class TestRateLimiter:
    def test_module_instance_is_singleton(self):
        """Module-level rate_limiter is accessed as the same instance across imports."""
        from core.rate_limiter import rate_limiter as rl2
        assert rate_limiter is rl2

    def test_module_instance_is_initialized(self):
        assert isinstance(rate_limiter, RateLimiter)
        assert hasattr(rate_limiter, "_req_times")
        assert hasattr(rate_limiter, "_tok_log")
        assert hasattr(rate_limiter, "_lock")

    def test_estimate_tokens_non_empty(self):
        assert estimate_tokens("hello world") > 0

    def test_estimate_tokens_empty(self):
        assert estimate_tokens("") == 1  # len("") // 4 + 1

    @pytest.mark.asyncio
    async def test_acquire_allows_normal_usage(self):
        rl = RateLimiter()
        await rl.acquire(estimated_tokens=100)
        assert len(rl._req_times) == 1
