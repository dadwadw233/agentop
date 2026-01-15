"""Parser for Claude Code stats-cache.json file."""

import json
from pathlib import Path
from datetime import date, datetime
from typing import Dict, Any, Optional
from ..core.models import TokenUsage, CostEstimate
from ..core.constants import CLAUDE_PRICING


class ClaudeStatsParser:
    """Parse Claude Code stats-cache.json for usage statistics."""

    def __init__(self, stats_file: Optional[str] = None):
        """
        Initialize parser.

        Args:
            stats_file: Path to stats-cache.json (default: ~/.claude/stats-cache.json)
        """
        if stats_file:
            self.stats_file = Path(stats_file).expanduser()
        else:
            self.stats_file = Path("~/.claude/stats-cache.json").expanduser()

    def parse_stats(self) -> Dict[str, Any]:
        """
        Parse the stats-cache.json file.

        Returns:
            Dictionary with usage statistics
        """
        if not self.stats_file.exists():
            return self._empty_stats()

        try:
            with open(self.stats_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"Error parsing stats file: {e}")
            return self._empty_stats()

    def get_today_usage(self) -> Dict[str, Any]:
        """
        Get usage for today.

        Returns:
            Dictionary with today's tokens, cost, and session info
        """
        stats = self.parse_stats()
        today = date.today().isoformat()

        # Find today's activity
        today_activity = None
        for activity in stats.get("dailyActivity", []):
            if activity["date"] == today:
                today_activity = activity
                break

        # Find today's tokens
        today_tokens = {}
        for token_data in stats.get("dailyModelTokens", []):
            if token_data["date"] == today:
                today_tokens = token_data.get("tokensByModel", {})
                break

        # Calculate totals
        total_tokens = sum(today_tokens.values())

        # Calculate cost (approximation, as we don't have input/output split in daily data)
        total_cost = self._estimate_cost_from_total(today_tokens)

        # Session info
        active_sessions = self._count_active_sessions(stats)

        return {
            "tokens": TokenUsage(
                input_tokens=int(total_tokens * 0.3),  # Rough estimate: 30% input
                output_tokens=int(total_tokens * 0.7),  # 70% output
            ),
            "cost": total_cost,
            "total_sessions": today_activity["sessionCount"] if today_activity else 0,
            "active_sessions": active_sessions,
            "message_count": today_activity["messageCount"] if today_activity else 0,
        }

    def get_stats_last_updated(self) -> Optional[datetime]:
        """
        Get the last modified time of the stats file.

        Returns:
            Datetime of last update, or None if unavailable
        """
        if not self.stats_file.exists():
            return None
        try:
            return datetime.fromtimestamp(self.stats_file.stat().st_mtime)
        except Exception:
            return None

    def get_month_usage(self) -> Dict[str, Any]:
        """
        Get usage for current month.

        Returns:
            Dictionary with month's tokens and cost
        """
        stats = self.parse_stats()
        today = date.today()
        current_month = today.strftime("%Y-%m")

        # Sum up all days in current month
        month_tokens = {}
        for token_data in stats.get("dailyModelTokens", []):
            if token_data["date"].startswith(current_month):
                for model, tokens in token_data.get("tokensByModel", {}).items():
                    month_tokens[model] = month_tokens.get(model, 0) + tokens

        total_tokens = sum(month_tokens.values())
        total_cost = self._estimate_cost_from_total(month_tokens)

        return {
            "tokens": TokenUsage(
                input_tokens=int(total_tokens * 0.3),
                output_tokens=int(total_tokens * 0.7),
            ),
            "cost": total_cost,
        }

    def get_total_usage(self) -> Dict[str, Any]:
        """
        Get total usage from modelUsage.

        Returns:
            Dictionary with total usage statistics
        """
        stats = self.parse_stats()
        model_usage = stats.get("modelUsage", {})

        total_input = 0
        total_output = 0
        total_cost = 0.0

        for model, usage in model_usage.items():
            input_tokens = usage.get("inputTokens", 0)
            output_tokens = usage.get("outputTokens", 0)

            total_input += input_tokens
            total_output += output_tokens

            # Calculate cost
            model_name = self._normalize_model_name(model)
            pricing = self._get_pricing(model_name)
            if pricing:
                total_cost += (input_tokens / 1_000_000) * pricing["input"]
                total_cost += (output_tokens / 1_000_000) * pricing["output"]

        return {
            "tokens": TokenUsage(
                input_tokens=total_input,
                output_tokens=total_output,
            ),
            "cost": total_cost,
            "total_sessions": stats.get("totalSessions", 0),
            "total_messages": stats.get("totalMessages", 0),
        }

    def _count_active_sessions(self, stats: Dict[str, Any]) -> int:
        """
        Count active sessions.

        Note: This is a rough estimate. The stats file may not be updated in real-time.
        Returns 0 if no recent activity detected.

        Args:
            stats: Parsed stats data

        Returns:
            Number of active sessions (estimated)
        """
        # Check if we have any sessions at all
        total_sessions = stats.get("totalSessions", 0)
        if total_sessions == 0:
            return 0

        # Check latest activity date
        last_computed = stats.get("lastComputedDate", "")
        today = date.today().isoformat()

        # If stats were updated today or yesterday, there might be active sessions
        # Note: This is an approximation since stats may not be real-time
        if last_computed >= today or last_computed == self._yesterday():
            # Return 0 for now, will be updated when we detect running processes
            return 0

        return 0

    def _yesterday(self) -> str:
        """Get yesterday's date as ISO string."""
        from datetime import timedelta
        yesterday = date.today() - timedelta(days=1)
        return yesterday.isoformat()

    def _estimate_cost_from_total(self, tokens_by_model: Dict[str, int]) -> float:
        """
        Estimate cost from total tokens by model.

        Args:
            tokens_by_model: Dictionary of model -> total tokens

        Returns:
            Estimated cost in USD
        """
        total_cost = 0.0

        for model, total_tokens in tokens_by_model.items():
            model_name = self._normalize_model_name(model)
            pricing = self._get_pricing(model_name)

            if pricing:
                # Estimate: 30% input, 70% output
                input_tokens = int(total_tokens * 0.3)
                output_tokens = int(total_tokens * 0.7)

                total_cost += (input_tokens / 1_000_000) * pricing["input"]
                total_cost += (output_tokens / 1_000_000) * pricing["output"]

        return total_cost

    def _normalize_model_name(self, model: str) -> str:
        """
        Normalize model name to match pricing keys.

        Args:
            model: Model name from stats (e.g., "claude-sonnet-4-5-20250929")

        Returns:
            Normalized model name
        """
        if "sonnet-4" in model or "sonnet-3.5" in model:
            return "claude-sonnet-4"
        elif "opus-4" in model:
            return "claude-opus-4"
        elif "haiku-4" in model:
            return "claude-haiku-4"
        return "claude-sonnet-4"  # Default

    def _get_pricing(self, model_name: str) -> Optional[Dict[str, float]]:
        """
        Get pricing for a model.

        Args:
            model_name: Normalized model name

        Returns:
            Pricing dictionary or None
        """
        return CLAUDE_PRICING.get(model_name)

    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty stats structure."""
        return {
            "version": 1,
            "dailyActivity": [],
            "dailyModelTokens": [],
            "modelUsage": {},
            "totalSessions": 0,
            "totalMessages": 0,
        }
