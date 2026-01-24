"""Index cache for OpenCode stats."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from ..core.models import OpenCodeTokenUsage


class OpenCodeIndexCache:
    """Cache index for OpenCode stats to enable incremental parsing."""

    def __init__(self, cache_path: Optional[Path] = None):
        """
        Initialize cache.

        Args:
            cache_path: Path to cache file (default: ~/.cache/agentop/opencode-index.json)
        """
        if cache_path:
            self.cache_path = cache_path
        else:
            self.cache_path = Path.home() / ".cache/agentop/opencode-index.json"

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load cache from disk."""
        if not self.cache_path.exists():
            return {}

        try:
            with open(self.cache_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self) -> None:
        """Save cache to disk."""
        with open(self.cache_path, "w") as f:
            json.dump(self.data, f, indent=2, default=str)

    def get_last_scan(self) -> datetime:
        """Get last scan timestamp."""
        ts = self.data.get("last_scan")
        if ts:
            return datetime.fromisoformat(ts)
        return datetime.fromtimestamp(0)

    def set_last_scan(self, timestamp: datetime) -> None:
        """Update last scan timestamp."""
        self.data["last_scan"] = timestamp.isoformat()
        self._save()

    def get_aggregate(self, key: str, field: str) -> Dict[str, OpenCodeTokenUsage]:
        """
        Get cached aggregate data.

        Args:
            key: Type of aggregate (by_session, by_project, by_model, by_agent, by_date)
            field: Field name in cache

        Returns:
            Dictionary of name -> OpenCodeTokenUsage
        """
        cached = self.data.get(field, {}).get(key, {})
        return {name: OpenCodeTokenUsage(**usage) for name, usage in cached.items()}

    def set_aggregate(self, key: str, field: str, data: Dict[str, OpenCodeTokenUsage]) -> None:
        """
        Update cached aggregate data.

        Args:
            key: Type of aggregate (by_session, by_project, by_model, by_agent, by_date)
            field: Field name in cache
            data: Dictionary of name -> OpenCodeTokenUsage
        """
        if field not in self.data:
            self.data[field] = {}

        self.data[field][key] = {
            name: {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "reasoning_tokens": usage.reasoning_tokens,
                "cache_read_tokens": usage.cache_read_tokens,
                "cache_write_tokens": usage.cache_write_tokens,
            }
            for name, usage in data.items()
        }
        self._save()

    def invalidate(self) -> None:
        """Invalidate cache (force full re-scan)."""
        self.data = {}
        self._save()
