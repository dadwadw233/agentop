"""Test OpenCode index cache."""

import pytest
from pathlib import Path
from datetime import datetime
from agentop.parsers.opencode_cache import OpenCodeIndexCache
from agentop.core.models import OpenCodeTokenUsage


def test_cache_initializes():
    """Cache initializes with default path."""
    cache = OpenCodeIndexCache()
    assert cache.cache_path.name == "opencode-index.json"


def test_cache_sets_and_gets_last_scan():
    """Cache stores and retrieves last scan timestamp."""
    cache = OpenCodeIndexCache()
    ts = datetime(2026, 1, 24, 12, 0, 0)

    cache.set_last_scan(ts)
    retrieved = cache.get_last_scan()

    assert retrieved == ts


def test_cache_sets_and_gets_aggregate():
    """Cache stores and retrieves aggregate data."""
    cache = OpenCodeIndexCache()
    data = {
        "test_key": OpenCodeTokenUsage(
            input_tokens=100,
            output_tokens=50,
            reasoning_tokens=10,
            cache_read_tokens=5,
            cache_write_tokens=2,
        )
    }

    cache.set_aggregate("all", "by_model", data)
    retrieved = cache.get_aggregate("all", "by_model")

    assert "test_key" in retrieved
    assert retrieved["test_key"].input_tokens == 100
    assert retrieved["test_key"].total_tokens == 167


def test_cache_invalidate_clears_data():
    """Cache invalidation clears all data."""
    cache = OpenCodeIndexCache()
    ts = datetime.now()

    cache.set_last_scan(ts)
    cache.invalidate()

    retrieved = cache.get_last_scan()
    assert retrieved == datetime.fromtimestamp(0)
