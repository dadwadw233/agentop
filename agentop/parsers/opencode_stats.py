"""Parser for OpenCode stats from local storage."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional, List
from ..core.models import OpenCodeTokenUsage, OpenCodeMessage, OpenCodeSession
from .opencode_cache import OpenCodeIndexCache


class OpenCodeStatsParser:
    """Parse OpenCode usage statistics from local storage."""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize parser.

        Args:
            storage_path: Path to OpenCode storage directory (default: ~/.local/share/opencode/storage)
        """
        if storage_path:
            self.storage_path = Path(storage_path).expanduser()
        else:
            self.storage_path = Path("~/.local/share/opencode/storage").expanduser()
        self.cache = OpenCodeIndexCache()

    def _parse_timestamp(self, value: Optional[int]) -> datetime:
        if not value:
            return datetime.fromtimestamp(0)
        seconds = value / 1000 if value > 1_000_000_000_000 else value
        return datetime.fromtimestamp(seconds)

    def parse_message(self, message_file: Path) -> Optional[OpenCodeMessage]:
        """
        Parse a single message JSON file.

        Args:
            message_file: Path to message JSON file

        Returns:
            OpenCodeMessage or None if parsing fails
        """
        if not message_file.exists():
            return None

        try:
            with open(message_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None

        try:
            tokens_data = data.get("tokens", {})
            cache_data = tokens_data.get("cache", {})

            message = OpenCodeMessage(
                message_id=data.get("id", ""),
                session_id=data.get("sessionID", ""),
                role=data.get("role", ""),
                model_id=data.get("modelID", ""),
                provider_id=data.get("providerID", ""),
                agent=data.get("agent"),
                project_path=data.get("path", {}).get("root"),
                created_at=self._parse_timestamp(data.get("time", {}).get("created")),
                completed_at=self._parse_timestamp(data.get("time", {}).get("completed"))
                if data.get("time", {}).get("completed")
                else None,
                tokens=OpenCodeTokenUsage(
                    input_tokens=tokens_data.get("input", 0),
                    output_tokens=tokens_data.get("output", 0),
                    reasoning_tokens=tokens_data.get("reasoning", 0),
                    cache_read_tokens=cache_data.get("read", 0),
                    cache_write_tokens=cache_data.get("write", 0),
                ),
            )
            return message
        except Exception:
            return None

    def parse_session(self, session_file: Path) -> Optional[OpenCodeSession]:
        """
        Parse a single session JSON file.

        Args:
            session_file: Path to session JSON file

        Returns:
            OpenCodeSession or None if parsing fails
        """
        if not session_file.exists():
            return None

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None

        try:
            tokens_data = data.get("tokens", {})
            cache_data = tokens_data.get("cache", {})

            session = OpenCodeSession(
                session_id=data.get("id", ""),
                start_time=self._parse_timestamp(data.get("time", {}).get("created")),
                end_time=self._parse_timestamp(data.get("time", {}).get("completed"))
                if data.get("time", {}).get("completed")
                else None,
                model_id=data.get("modelID"),
                provider_id=data.get("providerID"),
                agent=data.get("agent"),
                project_path=data.get("path", {}).get("root"),
                tokens=OpenCodeTokenUsage(
                    input_tokens=tokens_data.get("input", 0),
                    output_tokens=tokens_data.get("output", 0),
                    reasoning_tokens=tokens_data.get("reasoning", 0),
                    cache_read_tokens=cache_data.get("read", 0),
                    cache_write_tokens=cache_data.get("write", 0),
                ),
                message_count=data.get("messageCount", 0),
            )
            return session
        except Exception:
            return None

    def get_all_messages(self, time_range: str = "all") -> List[OpenCodeMessage]:
        """
        Get all messages from storage with caching.

        Args:
            time_range: Filter by time range (all, today, week, month)

        Returns:
            List of OpenCodeMessage objects
        """
        messages = []

        if not self.storage_path.exists():
            return messages

        message_dir = self.storage_path / "message"
        if not message_dir.exists():
            return messages

        last_scan = self.cache.get_last_scan()

        for session_dir in message_dir.iterdir():
            if not session_dir.is_dir():
                continue

            for message_file in session_dir.glob("*.json"):
                message = self.parse_message(message_file)
                if message and self._matches_time_range(message, time_range):
                    messages.append(message)

        if messages:
            latest_created = max(m.created_at for m in messages if m.created_at)
            self.cache.set_last_scan(latest_created)

        return messages

    def get_all_sessions(self) -> List[OpenCodeSession]:
        """
        Get all sessions from storage.

        Returns:
            List of OpenCodeSession objects
        """
        sessions = []

        if not self.storage_path.exists():
            return sessions

        session_dir = self.storage_path / "session"
        if not session_dir.exists():
            return sessions

        for session_file in session_dir.glob("*.json"):
            session = self.parse_session(session_file)
            if session:
                sessions.append(session)

        return sessions

    def aggregate_by_session(
        self, messages: List[OpenCodeMessage]
    ) -> Dict[str, OpenCodeTokenUsage]:
        """Aggregate token usage by session ID."""
        aggregates: Dict[str, OpenCodeTokenUsage] = {}

        for message in messages:
            if message.session_id not in aggregates:
                aggregates[message.session_id] = OpenCodeTokenUsage()

            aggregates[message.session_id].input_tokens += message.tokens.input_tokens
            aggregates[message.session_id].output_tokens += message.tokens.output_tokens
            aggregates[message.session_id].reasoning_tokens += message.tokens.reasoning_tokens
            aggregates[message.session_id].cache_read_tokens += message.tokens.cache_read_tokens
            aggregates[message.session_id].cache_write_tokens += message.tokens.cache_write_tokens

        return aggregates

    def aggregate_by_project(
        self, messages: List[OpenCodeMessage]
    ) -> Dict[str, OpenCodeTokenUsage]:
        """Aggregate token usage by project path."""
        aggregates: Dict[str, OpenCodeTokenUsage] = {}

        for message in messages:
            project = message.project_path or "unknown"
            if project not in aggregates:
                aggregates[project] = OpenCodeTokenUsage()

            aggregates[project].input_tokens += message.tokens.input_tokens
            aggregates[project].output_tokens += message.tokens.output_tokens
            aggregates[project].reasoning_tokens += message.tokens.reasoning_tokens
            aggregates[project].cache_read_tokens += message.tokens.cache_read_tokens
            aggregates[project].cache_write_tokens += message.tokens.cache_write_tokens

        return aggregates

    def aggregate_by_model(self, messages: List[OpenCodeMessage]) -> Dict[str, OpenCodeTokenUsage]:
        """Aggregate token usage by model ID."""
        aggregates: Dict[str, OpenCodeTokenUsage] = {}

        for message in messages:
            model = message.model_id or "unknown"
            if model not in aggregates:
                aggregates[model] = OpenCodeTokenUsage()

            aggregates[model].input_tokens += message.tokens.input_tokens
            aggregates[model].output_tokens += message.tokens.output_tokens
            aggregates[model].reasoning_tokens += message.tokens.reasoning_tokens
            aggregates[model].cache_read_tokens += message.tokens.cache_read_tokens
            aggregates[model].cache_write_tokens += message.tokens.cache_write_tokens

        return aggregates

    def aggregate_by_agent(self, messages: List[OpenCodeMessage]) -> Dict[str, OpenCodeTokenUsage]:
        """Aggregate token usage by agent."""
        aggregates: Dict[str, OpenCodeTokenUsage] = {}

        for message in messages:
            agent = message.agent or "unknown"
            if agent not in aggregates:
                aggregates[agent] = OpenCodeTokenUsage()

            aggregates[agent].input_tokens += message.tokens.input_tokens
            aggregates[agent].output_tokens += message.tokens.output_tokens
            aggregates[agent].reasoning_tokens += message.tokens.reasoning_tokens
            aggregates[agent].cache_read_tokens += message.tokens.cache_read_tokens
            aggregates[agent].cache_write_tokens += message.tokens.cache_write_tokens

        return aggregates

    def aggregate_by_date(self, messages: List[OpenCodeMessage]) -> Dict[str, OpenCodeTokenUsage]:
        """Aggregate token usage by date."""
        aggregates: Dict[str, OpenCodeTokenUsage] = {}

        for message in messages:
            date_str = message.created_at.date().isoformat()
            if date_str not in aggregates:
                aggregates[date_str] = OpenCodeTokenUsage()

            aggregates[date_str].input_tokens += message.tokens.input_tokens
            aggregates[date_str].output_tokens += message.tokens.output_tokens
            aggregates[date_str].reasoning_tokens += message.tokens.reasoning_tokens
            aggregates[date_str].cache_read_tokens += message.tokens.cache_read_tokens
            aggregates[date_str].cache_write_tokens += message.tokens.cache_write_tokens

        return aggregates

    def _matches_time_range(self, message: OpenCodeMessage, time_range: str) -> bool:
        """Check if message matches the given time range."""
        if time_range == "all":
            return True

        msg_date = message.created_at.date()
        today = date.today()

        if time_range == "today":
            return msg_date == today

        if time_range == "week":
            from datetime import timedelta

            week_ago = today - timedelta(days=7)
            return msg_date >= week_ago

        if time_range == "month":
            from datetime import timedelta

            month_ago = today - timedelta(days=30)
            return msg_date >= month_ago

        return True
