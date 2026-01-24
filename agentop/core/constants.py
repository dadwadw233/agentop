"""Constants and enumerations."""

from enum import Enum


class AgentType(str, Enum):
    """Supported agent types."""

    CLAUDE_CODE = "claude_code"
    COPILOT = "copilot"
    CODEX = "codex"
    OPENCODE = "opencode"


# Process detection patterns
AGENT_PATTERNS = {
    AgentType.CLAUDE_CODE: {
        "process_names": ["claude"],
        "cmdline_patterns": [
            r"\.local/bin/claude",
            r"--model\s+claude-",
        ],
        "min_memory_mb": 50,
    },
    AgentType.CODEX: {
        "process_names": ["codex"],
        "cmdline_patterns": [
            r"(?:^|/)codex(?:\s|$)",
            r"\bopenai[-_ ]?codex\b",
        ],
        "min_memory_mb": 40,
    },
    AgentType.OPENCODE: {
        "process_names": ["node"],
        "cmdline_patterns": [
            r"(?:^|/)node(?:\s+|$)",
            r"\bopencode\b",
        ],
        "min_memory_mb": 100,
    },
}

# Claude pricing (per 1M tokens)
CLAUDE_PRICING = {
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "claude-sonnet-3.5": {"input": 3.0, "output": 15.0},
    "claude-haiku-4": {"input": 0.25, "output": 1.25},
}

# Default paths
DEFAULT_CLAUDE_LOGS_DIR = "~/.claude-code/sessions/"
DEFAULT_CODEX_STATS_FILES = [
    "~/.codex/stats.json",
    "~/.codex/usage.json",
    "~/.codex/usage.jsonl",
    "~/.openai/codex/stats.json",
    "~/.openai/codex/usage.json",
    "~/.openai/codex/usage.jsonl",
    "~/.config/codex/stats.json",
    "~/.config/codex/usage.json",
    "~/.config/codex/usage.jsonl",
    "~/.config/openai/codex/stats.json",
    "~/.config/openai/codex/usage.json",
    "~/.config/openai/codex/usage.jsonl",
    "~/Library/Application Support/Codex/stats.json",
    "~/Library/Application Support/OpenAI/Codex/stats.json",
]
DEFAULT_CODEX_LOGS_DIRS = [
    "~/.codex/logs/",
    "~/.codex/sessions/",
    "~/.openai/codex/logs/",
    "~/.openai/codex/sessions/",
    "~/.config/codex/logs/",
    "~/.config/codex/sessions/",
    "~/Library/Application Support/Codex/logs/",
    "~/Library/Application Support/Codex/sessions/",
    "~/Library/Application Support/OpenAI/Codex/logs/",
    "~/Library/Application Support/OpenAI/Codex/sessions/",
]
