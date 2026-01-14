"""Parser for Claude Code session logs (JSONL format)."""

import json
import os
from pathlib import Path
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from ..core.models import SessionData, TokenUsage, CostEstimate
from ..core.constants import CLAUDE_PRICING, DEFAULT_CLAUDE_LOGS_DIR


class ClaudeLogParser:
    """Parse Claude Code JSONL session logs."""

    def __init__(self, logs_dir: Optional[str] = None):
        """
        Initialize parser.

        Args:
            logs_dir: Directory containing session logs (default: ~/.claude-code/sessions/)
        """
        if logs_dir:
            self.logs_dir = Path(logs_dir).expanduser()
        else:
            self.logs_dir = Path(DEFAULT_CLAUDE_LOGS_DIR).expanduser()

    def list_session_files(self, target_date: Optional[date] = None) -> List[Path]:
        """
        List all session log files, optionally filtered by date.

        Args:
            target_date: Filter by creation date (default: None, returns all)

        Returns:
            List of Path objects for session files
        """
        if not self.logs_dir.exists():
            return []

        session_files = []
        for file_path in self.logs_dir.glob("*.jsonl"):
            if target_date:
                # Filter by file modification date
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime.date() != target_date:
                    continue
            session_files.append(file_path)

        # Sort by modification time (newest first)
        session_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return session_files

    def parse_session_file(self, file_path: Path) -> SessionData:
        """
        Parse a single session JSONL file.

        Args:
            file_path: Path to the session file

        Returns:
            SessionData object with aggregated metrics
        """
        session_id = file_path.stem
        start_time = datetime.fromtimestamp(file_path.stat().st_ctime)
        end_time = datetime.fromtimestamp(file_path.stat().st_mtime)

        tokens = TokenUsage()
        cost = CostEstimate(0.0)
        message_count = 0
        model = None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)
                        self._process_entry(entry, tokens, cost)

                        # Track model and message count
                        if "model" in entry and not model:
                            model = entry["model"]
                        if entry.get("type") in ["request", "response"]:
                            message_count += 1

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

        return SessionData(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            model=model,
            tokens=tokens,
            cost=cost,
            message_count=message_count,
        )

    def _process_entry(
        self, entry: Dict[str, Any], tokens: TokenUsage, cost: CostEstimate
    ) -> None:
        """
        Process a single log entry and update tokens/cost.

        Args:
            entry: Parsed JSON entry
            tokens: TokenUsage object to update
            cost: CostEstimate object to update
        """
        # Extract usage from response entries
        if entry.get("type") == "response":
            usage = entry.get("usage", {})
            if usage:
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)

                tokens.input_tokens += input_tokens
                tokens.output_tokens += output_tokens

                # Calculate cost
                model = entry.get("model", "")
                cost.amount += self._estimate_cost(model, input_tokens, output_tokens)

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost based on model and token usage.

        Args:
            model: Model name (e.g., "claude-sonnet-4-5")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        # Try to match model to pricing
        pricing = None
        for model_key, prices in CLAUDE_PRICING.items():
            if model_key in model:
                pricing = prices
                break

        # Default to Sonnet pricing if not found
        if not pricing:
            pricing = CLAUDE_PRICING["claude-sonnet-4"]

        # Calculate cost (prices are per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def get_today_usage(self) -> Dict[str, Any]:
        """
        Get aggregated usage for today.

        Returns:
            Dictionary with total tokens, cost, and session count
        """
        today = date.today()
        session_files = self.list_session_files(target_date=today)

        total_tokens = TokenUsage()
        total_cost = 0.0
        session_count = len(session_files)
        active_sessions = 0

        for file_path in session_files:
            session = self.parse_session_file(file_path)
            total_tokens.input_tokens += session.tokens.input_tokens
            total_tokens.output_tokens += session.tokens.output_tokens
            total_cost += session.cost.amount

            # Consider session active if modified in last 10 minutes
            if session.end_time:
                age_minutes = (datetime.now() - session.end_time).total_seconds() / 60
                if age_minutes < 10:
                    active_sessions += 1

        return {
            "tokens": total_tokens,
            "cost": total_cost,
            "total_sessions": session_count,
            "active_sessions": active_sessions,
        }

    def get_month_usage(self) -> Dict[str, Any]:
        """
        Get aggregated usage for current month.

        Returns:
            Dictionary with total tokens and cost
        """
        today = date.today()
        all_files = self.list_session_files()

        total_tokens = TokenUsage()
        total_cost = 0.0

        for file_path in all_files:
            # Check if file is from this month
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime.year != today.year or mtime.month != today.month:
                continue

            session = self.parse_session_file(file_path)
            total_tokens.input_tokens += session.tokens.input_tokens
            total_tokens.output_tokens += session.tokens.output_tokens
            total_cost += session.cost.amount

        return {
            "tokens": total_tokens,
            "cost": total_cost,
        }
