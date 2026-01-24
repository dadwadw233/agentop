# Agentop

A terminal UI tool for monitoring local AI coding agents — like `nvtop`/`htop`, but for Claude/Codex.

## Features

- Real-time process monitoring (CPU, memory, uptime)
- Claude Code usage + cost from local stats
- Quota panels (beta) for Codex + Antigravity
- Lightweight Textual TUI

## Supported Agents

| Agent | Process Monitor | Usage Stats | Quota | Status |
|-------|----------------|-------------|-------|--------|
| **Claude Code** | ✅ | ✅ | ✅ | Stable |
| **Antigravity** | ⏳ | ⏳ | ✅ | Beta |
| **OpenAI Codex** | ✅ | ✅ | ✅ | Beta |
| **OpenCode** | ✅ | ✅ | ⏳ | Beta |

## Supported Platforms (has been tested)

- macOS
- Linux

## Installation (macOS / Linux)

### PyPI
```bash
pip install agentop
```

### From source
```bash
pip install git+https://github.com/dadwadw233/agentop.git
```

## Quick Start

```bash
# TUI
agentop

# Or
python3 -m agentop
```

Detailed stats:
```bash
python3 show_stats.py
```

## Data Sources

- Claude stats: `~/.claude/stats-cache.json`
- Codex usage/quota: `/usage` API via Codex auth (`~/.codex/auth.json`)
- Antigravity quota: Google Cloud Code API via Antigravity auth (local state db)
- OpenCode stats: `~/.local/share/opencode/storage/` (message + session directories)

## Changelog

### 0.2.0 (2026-01-25)

**OpenCode Features:**
- Fixed time filtering bug - now shows all historical data (not just today)
- Added time range support (Today/Week/Month/All) for all views
- Implemented lazy loading - only computes aggregates needed for current view
- Added index cache for faster incremental parsing
- Performance optimizations for large datasets

**TUI Improvements:**
- Redesigned overview dashboard with structured layout (Process Status, Session Stats, Token Usage)
- Added progress bars for visual token usage comparison
- Implemented pagination for handling large datasets
- Dynamic page sizing based on available screen height
- Enhanced table formatting with better alignment and smart truncation
- Color gradients for usage intensity (cyan/magenta/blue)
- Visual status indicators (🟢/⚪) with colored borders
- Improved hint text with time range display and update timestamps
- Consistent styling across all sub-views (Sessions, Projects, Models, Agents, Timeline)

## Roadmap

- More agents (TBD)
- Config file (YAML)
- History + export (CSV/JSON)
- UI polish

## Known Limitations

- Claude stats can lag behind real time
- Codex usage is fetched from the API (not local files)
- Antigravity quota depends on account access
- Antigravity refresh requires `ANTIGRAVITY_OAUTH_CLIENT_SECRET` or a fresh login
- Proxy users: if you see “unknown scheme for proxy URL”, set `AGENTOP_DISABLE_PROXY=1` or install `httpx[socks]`

## License

MIT (see `LICENSE`)
