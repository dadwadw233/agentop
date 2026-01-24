"""Tests for OpenCode models."""

from agentop.core.models import OpenCodeTokenUsage


def test_opencode_token_usage_total_counts_cache():
    usage = OpenCodeTokenUsage(
        input_tokens=10,
        output_tokens=5,
        reasoning_tokens=2,
        cache_read_tokens=3,
        cache_write_tokens=4,
    )
    assert usage.total_tokens == 24
