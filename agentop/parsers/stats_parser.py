"""Parser for Claude Code JSONL usage data."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Any, Optional, Iterable, Set, Tuple

from ..core.constants import (
    CLAUDE_CONFIG_DIR_ENV,
    CLAUDE_PROJECTS_DIRNAME,
    DEFAULT_CLAUDE_CONFIG_DIRS,
    CLAUDE_PRICING,
)
from ..parsers.litellm_pricing import LiteLLMCostCalculator
from ..core.models import TokenUsage, CostEstimate


@dataclass
class _UsageEntry:
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    model: Optional[str]
    cost_usd: Optional[float]
    session_id: Optional[str]


class ClaudeStatsParser:
    """Parse Claude Code JSONL usage data under ~/.config/claude/projects."""

    def __init__(self, stats_file: Optional[str] = None, cache_ttl_seconds: int = 10):
        """
        Initialize parser.

        Args:
            stats_file: Optional custom Claude data directory or JSONL file
            cache_ttl_seconds: Cache usage aggregation for N seconds
        """
        self._custom_path = Path(stats_file).expanduser() if stats_file else None
        self._usage_cache: Optional[Dict[str, Any]] = None
        self._last_scan: Optional[datetime] = None
        self._last_updated: Optional[datetime] = None
        self.cache_ttl_seconds = max(2, cache_ttl_seconds)
        self._cost_calculator = LiteLLMCostCalculator()

    def get_today_usage(self) -> Dict[str, Any]:
        """
        Get usage for today.

        Returns:
            Dictionary with today's tokens, cost, and session info
        """
        usage = self._collect_usage()
        today = date.today()
        bucket = usage["buckets"].get(today)
        return self._format_bucket(bucket)

    def get_month_usage(self) -> Dict[str, Any]:
        """
        Get usage for current month.

        Returns:
            Dictionary with month's tokens and cost
        """
        usage = self._collect_usage()
        today = date.today()
        total_tokens = TokenUsage()
        total_cost = 0.0
        cost_seen = False

        for usage_date, bucket in usage["buckets"].items():
            if usage_date.year != today.year or usage_date.month != today.month:
                continue
            total_tokens.input_tokens += bucket["tokens"].input_tokens
            total_tokens.output_tokens += bucket["tokens"].output_tokens
            total_tokens.cache_write_tokens += bucket["tokens"].cache_write_tokens
            total_tokens.cache_read_tokens += bucket["tokens"].cache_read_tokens
            if bucket["cost_seen"]:
                total_cost += bucket["cost"]
                cost_seen = True

        return {
            "tokens": total_tokens,
            "cost": total_cost if cost_seen else 0.0,
        }

    def get_stats_last_updated(self) -> Optional[datetime]:
        """
        Get the last modified time of the newest Claude JSONL file.

        Returns:
            Datetime of last update, or None if unavailable
        """
        self._collect_usage()
        return self._last_updated

    def _collect_usage(self) -> Dict[str, Any]:
        if self._usage_cache is not None and self._last_scan:
            age = (datetime.now() - self._last_scan).total_seconds()
            if age < self.cache_ttl_seconds:
                return self._usage_cache

        if self._usage_cache is not None and not self._last_scan:
            return self._usage_cache

        buckets: Dict[date, Dict[str, Any]] = {}
        self._last_updated = None

        processed_hashes: Set[str] = set()
        for file_path in self._iter_usage_files():
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if self._last_updated is None or mtime > self._last_updated:
                    self._last_updated = mtime
            except Exception:
                pass

            for entry in self._iter_entries(file_path, processed_hashes):
                if entry.timestamp.tzinfo:
                    entry_date = entry.timestamp.astimezone().date()
                else:
                    entry_date = entry.timestamp.date()
                bucket = buckets.setdefault(
                    entry_date,
                    {
                        "tokens": TokenUsage(),
                        "cost": 0.0,
                        "cost_seen": False,
                        "sessions": set(),
                    },
                )
                bucket["tokens"].input_tokens += entry.input_tokens
                bucket["tokens"].output_tokens += entry.output_tokens
                bucket["tokens"].cache_write_tokens += entry.cache_write_tokens
                bucket["tokens"].cache_read_tokens += entry.cache_read_tokens
                if entry.session_id:
                    bucket["sessions"].add(entry.session_id)
                if entry.cost_usd is not None:
                    bucket["cost"] += entry.cost_usd
                    bucket["cost_seen"] = True

        self._usage_cache = {"buckets": buckets}
        self._last_scan = datetime.now()
        return self._usage_cache

    def _format_bucket(self, bucket: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not bucket:
            return {
                "tokens": TokenUsage(),
                "cost": 0.0,
                "total_sessions": 0,
            }

        return {
            "tokens": bucket["tokens"],
            "cost": bucket["cost"] if bucket["cost_seen"] else 0.0,
            "total_sessions": len(bucket["sessions"]),
        }

    def _iter_usage_files(self) -> Iterable[Path]:
        config_dirs = self._resolve_config_dirs()
        for config_dir in config_dirs:
            projects_dir = config_dir / CLAUDE_PROJECTS_DIRNAME
            if not projects_dir.exists():
                continue
            for file_path in projects_dir.rglob("*.jsonl"):
                if file_path.is_file():
                    yield file_path

    def _resolve_config_dirs(self) -> Iterable[Path]:
        if self._custom_path:
            paths = self._expand_paths(str(self._custom_path))
            resolved = self._normalize_config_dirs(paths)
            if resolved:
                return resolved
            return []

        env_paths = os.environ.get(CLAUDE_CONFIG_DIR_ENV, "").strip()
        if env_paths:
            paths = self._expand_paths(env_paths)
            resolved = self._normalize_config_dirs(paths)
            if resolved:
                return resolved
            return []

        return self._normalize_config_dirs(DEFAULT_CLAUDE_CONFIG_DIRS)

    def _expand_paths(self, raw: str) -> Iterable[Path]:
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            yield Path(part).expanduser()

    def _normalize_config_dirs(self, paths: Iterable[Path | str]) -> Tuple[Path, ...]:
        resolved: list[Path] = []
        seen: set[Path] = set()
        for path in paths:
            if not isinstance(path, Path):
                path = Path(path)
            path = path.expanduser()
            if path.is_file() and path.suffix == ".jsonl":
                # Treat as explicit JSONL file path by using its parent dir.
                path = path.parent
            if path.name == CLAUDE_PROJECTS_DIRNAME:
                path = path.parent
            if not path.exists():
                continue
            if path in seen:
                continue
            projects_dir = path / CLAUDE_PROJECTS_DIRNAME
            if projects_dir.exists():
                resolved.append(path)
                seen.add(path)
        return tuple(resolved)

    def _iter_entries(
        self, file_path: Path, processed_hashes: Set[str]
    ) -> Iterable[_UsageEntry]:
        session_id = self._extract_session_id(file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = self._parse_line(line, processed_hashes, session_id)
                    if entry:
                        yield entry
        except Exception:
            return

    def _parse_line(
        self, line: str, processed_hashes: Set[str], session_id: Optional[str]
    ) -> Optional[_UsageEntry]:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None

        message = data.get("message")
        if not isinstance(message, dict):
            return None
        usage = message.get("usage")
        if not isinstance(usage, dict):
            return None

        unique_hash = self._create_unique_hash(message, data)
        if unique_hash:
            if unique_hash in processed_hashes:
                return None
            processed_hashes.add(unique_hash)

        timestamp_raw = data.get("timestamp")
        timestamp = self._parse_timestamp(timestamp_raw)
        if not timestamp:
            return None

        input_tokens = int(usage.get("input_tokens", 0) or 0)
        output_tokens = int(usage.get("output_tokens", 0) or 0)
        cache_write_tokens = int(usage.get("cache_creation_input_tokens", 0) or 0)
        cache_read_tokens = int(usage.get("cache_read_input_tokens", 0) or 0)
        model = message.get("model") or data.get("model")
        cost_usd = None
        if isinstance(data.get("costUSD"), (int, float)):
            cost_usd = float(data["costUSD"])
        else:
            cost_usd = self._estimate_cost(
                model,
                input_tokens,
                output_tokens,
                cache_write_tokens,
                cache_read_tokens,
            )

        return _UsageEntry(
            timestamp=timestamp,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_write_tokens=cache_write_tokens,
            cache_read_tokens=cache_read_tokens,
            model=model,
            cost_usd=cost_usd,
            session_id=session_id,
        )

    def _create_unique_hash(self, message: Dict[str, Any], data: Dict[str, Any]) -> Optional[str]:
        message_id = message.get("id")
        request_id = data.get("requestId")
        if not message_id or not request_id:
            return None
        return f"{message_id}:{request_id}"

    def _parse_timestamp(self, raw: Any) -> Optional[datetime]:
        if not isinstance(raw, str):
            return None
        ts = raw.strip()
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return None

    def _extract_session_id(self, file_path: Path) -> Optional[str]:
        if file_path.name == "usage.jsonl" or file_path.name == "chat.jsonl":
            return file_path.parent.name
        if file_path.suffix == ".jsonl":
            return file_path.stem
        return None

    def _estimate_cost(
        self,
        model: Optional[str],
        input_tokens: int,
        output_tokens: int,
        cache_write_tokens: int,
        cache_read_tokens: int,
    ) -> float:
        if not model:
            return 0.0

        cost = self._cost_calculator.calculate_cost(
            model,
            input_tokens,
            output_tokens,
            cache_write_tokens,
            cache_read_tokens,
        )
        if cost > 0:
            return cost

        pricing = None
        for model_key, prices in CLAUDE_PRICING.items():
            if model_key in model:
                pricing = prices
                break
        if not pricing:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
