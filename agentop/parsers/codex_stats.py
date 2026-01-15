"""Parser for OpenAI Codex usage stats and logs."""

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.constants import DEFAULT_CODEX_LOGS_DIRS, DEFAULT_CODEX_STATS_FILES
from ..core.models import CostEstimate, TokenUsage


class CodexStatsParser:
    """Parse Codex usage stats and log files."""

    def __init__(
        self,
        stats_file: Optional[str] = None,
        logs_dir: Optional[str] = None,
    ):
        """
        Initialize parser.

        Args:
            stats_file: Optional path to a stats JSON/JSONL file
            logs_dir: Optional directory containing JSONL logs
        """
        stats_file_env = os.environ.get("CODEX_STATS_FILE") or os.environ.get(
            "OPENAI_CODEX_STATS_FILE"
        )
        logs_dir_env = os.environ.get("CODEX_LOGS_DIR") or os.environ.get(
            "OPENAI_CODEX_LOGS_DIR"
        )

        stats_path = stats_file or stats_file_env
        logs_path = logs_dir or logs_dir_env

        self.stats_file = Path(stats_path).expanduser() if stats_path else None
        self.logs_dir = Path(logs_path).expanduser() if logs_path else None
        self.resolved_stats_file = self._resolve_stats_file()
        self.resolved_logs_dir = self._resolve_logs_dir()
        self._usage_cache: Optional[Dict[str, Any]] = None
        self._last_scan: Optional[datetime] = None
        self.cache_ttl_seconds = 5

    def get_today_usage(self) -> Optional[Dict[str, Any]]:
        """
        Get usage for today.

        Returns:
            Dictionary with tokens, cost, session count, and source, or None if no data
        """
        usage = self._collect_usage()
        if usage is None:
            return None

        today = date.today()
        bucket = usage["buckets"].get(today)
        return self._format_bucket(bucket, usage["source"])

    def get_month_usage(self) -> Optional[Dict[str, Any]]:
        """
        Get usage for current month.

        Returns:
            Dictionary with tokens, cost, and source, or None if no data
        """
        usage = self._collect_usage()
        if usage is None:
            return None

        today = date.today()
        total_tokens = TokenUsage()
        total_cost = 0.0
        cost_seen = False
        total_sessions = 0

        for usage_date, bucket in usage["buckets"].items():
            if usage_date.year != today.year or usage_date.month != today.month:
                continue
            total_tokens.input_tokens += bucket["tokens"].input_tokens
            total_tokens.output_tokens += bucket["tokens"].output_tokens
            total_sessions += len(bucket["sessions"])
            if bucket["cost_seen"]:
                total_cost += bucket["cost"]
                cost_seen = True

        return {
            "tokens": total_tokens,
            "cost": CostEstimate(total_cost) if cost_seen else None,
            "total_sessions": total_sessions,
            "source": usage["source"],
        }

    def _collect_usage(self) -> Optional[Dict[str, Any]]:
        if self._usage_cache is not None and self._last_scan:
            age = (datetime.now() - self._last_scan).total_seconds()
            if age < self.cache_ttl_seconds:
                return self._usage_cache

        if self._usage_cache is not None and not self._last_scan:
            return self._usage_cache

        buckets: Dict[date, Dict[str, Any]] = {}
        source = None

        if self.resolved_stats_file:
            self._parse_stats_file(self.resolved_stats_file, buckets)
            if buckets:
                source = str(self.resolved_stats_file)

        if not buckets and self.resolved_logs_dir:
            self._parse_logs_dir(self.resolved_logs_dir, buckets)
            if buckets:
                source = str(self.resolved_logs_dir)

        if not buckets:
            return None

        self._usage_cache = {"buckets": buckets, "source": source}
        self._last_scan = datetime.now()
        return self._usage_cache

    def _format_bucket(
        self, bucket: Optional[Dict[str, Any]], source: Optional[str]
    ) -> Dict[str, Any]:
        if not bucket:
            return {
                "tokens": TokenUsage(),
                "cost": None,
                "total_sessions": 0,
                "source": source,
            }

        return {
            "tokens": bucket["tokens"],
            "cost": CostEstimate(bucket["cost"]) if bucket["cost_seen"] else None,
            "total_sessions": len(bucket["sessions"]),
            "source": source,
        }

    def _resolve_stats_file(self) -> Optional[Path]:
        if self.stats_file and self.stats_file.exists():
            return self.stats_file

        for path in DEFAULT_CODEX_STATS_FILES:
            candidate = Path(path).expanduser()
            if candidate.exists():
                return candidate
        return None

    def _resolve_logs_dir(self) -> Optional[Path]:
        if self.logs_dir and self.logs_dir.exists():
            return self.logs_dir

        for path in DEFAULT_CODEX_LOGS_DIRS:
            candidate = Path(path).expanduser()
            if candidate.exists():
                return candidate
        return None

    def _parse_stats_file(self, file_path: Path, buckets: Dict[date, Dict[str, Any]]) -> None:
        if file_path.suffix.lower() == ".jsonl":
            self._parse_log_file(file_path, buckets)
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        self._extract_stats_entries(data, buckets, session_id=file_path.stem)

    def _parse_logs_dir(self, logs_dir: Path, buckets: Dict[date, Dict[str, Any]]) -> None:
        patterns = ("*.jsonl", "*.log", "*.json")
        for pattern in patterns:
            for file_path in logs_dir.glob(pattern):
                if file_path.is_dir():
                    continue
                if file_path.suffix.lower() == ".json":
                    self._parse_stats_file(file_path, buckets)
                else:
                    self._parse_log_file(file_path, buckets)

    def _parse_log_file(self, file_path: Path, buckets: Dict[date, Dict[str, Any]]) -> None:
        fallback_date = datetime.fromtimestamp(file_path.stat().st_mtime).date()
        default_session = file_path.stem

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    usage = self._extract_usage(entry)
                    if not usage:
                        continue

                    entry_date = self._extract_date(entry) or fallback_date
                    cost = self._extract_cost(entry)
                    session_id = self._extract_session_id(entry) or default_session
                    self._add_usage(buckets, entry_date, usage, cost, session_id)
        except Exception:
            return

    def _extract_stats_entries(
        self,
        data: Any,
        buckets: Dict[date, Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> None:
        if isinstance(data, dict) and self._extract_date_keyed_usage(data, buckets):
            return

        if isinstance(data, dict):
            for key in (
                "daily",
                "dailyUsage",
                "daily_usage",
                "usage",
                "records",
                "history",
            ):
                entries = data.get(key)
                if isinstance(entries, list):
                    for entry in entries:
                        self._process_entry(entry, buckets, session_id=session_id)
                    return
                if isinstance(entries, dict) and self._extract_date_keyed_usage(
                    entries, buckets
                ):
                    return

            self._process_entry(data, buckets, session_id=session_id)
            return

        if isinstance(data, list):
            for entry in data:
                self._process_entry(entry, buckets, session_id=session_id)

    def _extract_date_keyed_usage(
        self, data: Dict[str, Any], buckets: Dict[date, Dict[str, Any]]
    ) -> bool:
        found = False
        for key, value in data.items():
            entry_date = self._parse_date(key)
            if entry_date and isinstance(value, dict):
                self._process_entry(
                    value,
                    buckets,
                    session_id=f"stats-{entry_date.isoformat()}",
                    entry_date=entry_date,
                )
                found = True
        return found

    def _process_entry(
        self,
        entry: Any,
        buckets: Dict[date, Dict[str, Any]],
        session_id: Optional[str] = None,
        entry_date: Optional[date] = None,
    ) -> None:
        if not isinstance(entry, dict):
            return

        usage = self._extract_usage(entry)
        if not usage:
            return

        entry_date = entry_date or self._extract_date(entry)
        if not entry_date:
            return

        cost = self._extract_cost(entry)
        session_id = self._extract_session_id(entry) or session_id
        self._add_usage(buckets, entry_date, usage, cost, session_id)

    def _extract_usage(self, entry: Dict[str, Any]) -> Optional[TokenUsage]:
        usage_dict = self._find_usage_dict(entry) or entry
        if not isinstance(usage_dict, dict):
            return None

        input_tokens = self._get_int_value(
            usage_dict,
            (
                "input_tokens",
                "inputTokens",
                "prompt_tokens",
                "promptTokens",
                "request_tokens",
                "requestTokens",
            ),
        )
        output_tokens = self._get_int_value(
            usage_dict,
            (
                "output_tokens",
                "outputTokens",
                "completion_tokens",
                "completionTokens",
                "response_tokens",
                "responseTokens",
            ),
        )
        total_tokens = self._get_int_value(
            usage_dict, ("total_tokens", "totalTokens", "tokens", "token_count")
        )

        if input_tokens is None and output_tokens is None and total_tokens is None:
            return None

        if input_tokens is None and output_tokens is None and total_tokens is not None:
            input_tokens = total_tokens // 2
            output_tokens = total_tokens - input_tokens

        return TokenUsage(
            input_tokens=input_tokens or 0,
            output_tokens=output_tokens or 0,
        )

    def _find_usage_dict(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        usage = entry.get("usage")
        if isinstance(usage, dict):
            return usage

        for key in ("response", "result", "data", "output"):
            nested = entry.get(key)
            if isinstance(nested, dict):
                nested_usage = nested.get("usage")
                if isinstance(nested_usage, dict):
                    return nested_usage
        return None

    def _extract_cost(self, entry: Dict[str, Any]) -> Optional[float]:
        for key in ("cost", "cost_usd", "total_cost", "usd_cost", "price"):
            value = entry.get(key)
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    continue

        usage = self._find_usage_dict(entry)
        if isinstance(usage, dict):
            for key in ("cost", "cost_usd", "total_cost", "usd_cost", "price"):
                value = usage.get(key)
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str):
                    try:
                        return float(value)
                    except ValueError:
                        continue
        return None

    def _extract_date(self, entry: Dict[str, Any]) -> Optional[date]:
        for key in ("date", "day", "created_at", "created", "timestamp", "time", "ts"):
            if key in entry:
                parsed = self._parse_date(entry.get(key))
                if parsed:
                    return parsed
        return None

    def _parse_date(self, value: Any) -> Optional[date]:
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value).date()
            except (OSError, OverflowError, ValueError):
                return None

        if isinstance(value, str):
            text = value.strip()
            if len(text) >= 10:
                try:
                    return date.fromisoformat(text[:10])
                except ValueError:
                    pass
            try:
                cleaned = text.replace("Z", "").replace("z", "")
                return datetime.fromisoformat(cleaned).date()
            except ValueError:
                return None
        return None

    def _extract_session_id(self, entry: Dict[str, Any]) -> Optional[str]:
        for key in (
            "session_id",
            "sessionId",
            "conversation_id",
            "conversationId",
            "run_id",
            "runId",
        ):
            value = entry.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    def _get_int_value(self, data: Dict[str, Any], keys: tuple) -> Optional[int]:
        for key in keys:
            if key not in data:
                continue
            value = data.get(key)
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                try:
                    return int(float(value))
                except ValueError:
                    continue
        return None

    def _add_usage(
        self,
        buckets: Dict[date, Dict[str, Any]],
        usage_date: date,
        usage: TokenUsage,
        cost: Optional[float],
        session_id: Optional[str],
    ) -> None:
        if usage_date not in buckets:
            buckets[usage_date] = {
                "tokens": TokenUsage(),
                "cost": 0.0,
                "cost_seen": False,
                "sessions": set(),
            }

        bucket = buckets[usage_date]
        bucket["tokens"].input_tokens += usage.input_tokens
        bucket["tokens"].output_tokens += usage.output_tokens
        if cost is not None:
            bucket["cost"] += cost
            bucket["cost_seen"] = True
        if session_id:
            bucket["sessions"].add(session_id)
