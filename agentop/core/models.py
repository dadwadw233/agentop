"""Data models for Agentop."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class ProcessStatus(str, Enum):
    """Process status."""

    RUNNING = "running"
    SLEEPING = "sleeping"
    IDLE = "idle"
    ZOMBIE = "zombie"
    STOPPED = "stopped"


@dataclass
class ProcessMetrics:
    """Metrics for a single process."""

    pid: int
    name: str
    cmdline: str
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    num_threads: int
    create_time: datetime
    status: ProcessStatus

    @property
    def uptime(self) -> float:
        """Return uptime in seconds."""
        return (datetime.now() - self.create_time).total_seconds()


@dataclass
class TokenUsage:
    """Token usage statistics."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens


@dataclass
class OpenCodeTokenUsage:
    """OpenCode-specific token usage statistics with cache and reasoning tokens."""

    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used including reasoning and cache."""
        return (
            self.input_tokens
            + self.output_tokens
            + self.reasoning_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
        )


@dataclass
class CostEstimate:
    """Cost estimation."""

    amount: float  # in USD
    currency: str = "USD"


@dataclass
class RateLimitWindow:
    """Rate limit window snapshot."""

    used_percent: float
    window_minutes: Optional[int] = None
    resets_at: Optional[datetime] = None

    @property
    def remaining_percent(self) -> float:
        """Percent remaining in this window."""
        return max(0.0, 100.0 - self.used_percent)


@dataclass
class CreditsSnapshot:
    """Credits snapshot."""

    has_credits: bool
    unlimited: bool
    balance: Optional[str] = None


@dataclass
class RateLimitSnapshot:
    """Rate limit snapshot with primary/secondary windows."""

    primary: Optional[RateLimitWindow] = None
    secondary: Optional[RateLimitWindow] = None
    credits: Optional[CreditsSnapshot] = None
    plan_type: Optional[str] = None
    captured_at: Optional[datetime] = None


@dataclass
class AgentMetrics:
    """Base metrics for any agent."""

    agent_type: str
    processes: List[ProcessMetrics] = field(default_factory=list)
    is_active: bool = False
    last_active: Optional[datetime] = None

    @property
    def total_cpu(self) -> float:
        """Total CPU usage across all processes."""
        return sum(p.cpu_percent for p in self.processes)

    @property
    def total_memory_mb(self) -> float:
        """Total memory usage in MB."""
        return sum(p.memory_mb for p in self.processes)

    @property
    def process_count(self) -> int:
        """Number of processes."""
        return len(self.processes)


@dataclass
class ClaudeCodeMetrics(AgentMetrics):
    """Metrics specific to Claude Code."""

    agent_type: str = "claude_code"

    # Session info
    active_sessions: int = 0
    total_sessions_today: int = 0

    # Token usage
    tokens_today: TokenUsage = field(default_factory=TokenUsage)
    tokens_this_month: TokenUsage = field(default_factory=TokenUsage)

    # Cost
    cost_today: CostEstimate = field(default_factory=lambda: CostEstimate(0.0))
    cost_this_month: CostEstimate = field(default_factory=lambda: CostEstimate(0.0))

    # Stats metadata
    stats_last_updated: Optional[datetime] = None

    # Rate limits (quota)
    rate_limits: Optional[RateLimitSnapshot] = None
    rate_limits_source: Optional[str] = None
    rate_limits_error: Optional[str] = None


@dataclass
class CodexMetrics(AgentMetrics):
    """Metrics specific to OpenAI Codex."""

    agent_type: str = "codex"

    # Session info
    active_sessions: int = 0
    total_sessions_today: int = 0

    # Token usage
    tokens_today: TokenUsage = field(default_factory=TokenUsage)
    tokens_this_month: TokenUsage = field(default_factory=TokenUsage)

    # Cost (optional if logs don't include pricing)
    cost_today: Optional[CostEstimate] = None
    cost_this_month: Optional[CostEstimate] = None

    # Usage metadata
    usage_source: Optional[str] = None

    # Rate limits
    rate_limits: Optional[RateLimitSnapshot] = None
    rate_limits_source: Optional[str] = None
    rate_limits_error: Optional[str] = None


@dataclass
class SessionData:
    """Data from a single Claude Code session."""

    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    model: Optional[str] = None
    tokens: TokenUsage = field(default_factory=TokenUsage)
    cost: CostEstimate = field(default_factory=lambda: CostEstimate(0.0))
    message_count: int = 0


@dataclass
class OpenCodeMessage:
    """Data from a single OpenCode message."""

    message_id: str
    session_id: str
    role: str
    model_id: str
    provider_id: str
    agent: Optional[str] = None
    project_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    tokens: OpenCodeTokenUsage = field(default_factory=OpenCodeTokenUsage)


@dataclass
class OpenCodeSession:
    """Data from a single OpenCode session."""

    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    model_id: Optional[str] = None
    provider_id: Optional[str] = None
    agent: Optional[str] = None
    project_path: Optional[str] = None
    tokens: OpenCodeTokenUsage = field(default_factory=OpenCodeTokenUsage)
    message_count: int = 0


@dataclass
class OpenCodeMetrics(AgentMetrics):
    """Metrics specific to OpenCode."""

    agent_type: str = "opencode"

    active_sessions: int = 0
    total_sessions_today: int = 0

    total_tokens: OpenCodeTokenUsage = field(default_factory=OpenCodeTokenUsage)
    tokens_today: OpenCodeTokenUsage = field(default_factory=OpenCodeTokenUsage)

    by_session: dict = field(default_factory=dict)
    by_agent: dict = field(default_factory=dict)
    by_model: dict = field(default_factory=dict)
    by_provider: dict = field(default_factory=dict)
    by_project: dict = field(default_factory=dict)
    by_date: dict = field(default_factory=dict)

    stats_last_updated: Optional[datetime] = None
