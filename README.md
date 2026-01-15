# Agent Monitor

A terminal UI tool for monitoring local AI coding agents (Claude Code, Cursor, Copilot, etc.) - like `nvtop` for AI agents.

![Agent Monitor](https://img.shields.io/badge/status-MVP%20Complete-success)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

✅ **Real-time Process Monitoring**: Track CPU, memory, and running time of agent processes
✅ **Token Usage Tracking**: Monitor API token consumption from local stats
✅ **Cost Estimation**: Automatic cost calculation based on Claude pricing
✅ **Session Management**: View active sessions and usage statistics
✅ **Beautiful TUI**: Terminal UI with live updates (1-second refresh)
✅ **Local-First**: Works entirely from local data, no API required

## Supported Agents

| Agent | Process Monitor | Usage Stats | Cost Tracking | Status |
|-------|----------------|-------------|---------------|--------|
| **Claude Code** | ✅ | ✅ | ✅ | **MVP Complete** |
| **Cursor** | ✅ | ⚠️ | ⚠️ | Dashboard usage (unstable) |
| **GitHub Copilot** | ⏳ | ⏳ | ⏳ | Planned |
| **OpenAI Codex** | ✅ | ⏳ | ⏳ | Process monitoring + local logs (beta) |

## Installation

```bash
# Clone or navigate to the project
cd agent-monitor

# Install in development mode
pip install -e .
```

## Quick Start

### 1. Real-time TUI (Recommended)
```bash
# Run the interactive terminal UI
agent-monitor

# Or use Python module
python3 -m agent_monitor

# Or use the shell script
./run_tui.sh
```

**TUI Preview:**
```
┌─ 🤖 CLAUDE CODE 🟢 Active ─────────────────────────────┐
│ Processes:     1 running                                │
│                PID 54430                                 │
│ CPU:           0.0% ███░░░░░░░░░░░░░                    │
│ Memory:        451 MB                                    │
│ Uptime:        10.6 hours                                │
│                                                          │
│ Sessions:      1 active • 0 today                        │
│                                                          │
│ Tokens (Month): 320,098 total                           │
│   Input:       96,029 ███░░░░░░░░░░░░░ 30%             │
│   Output:      224,069 ███████████░░░░ 70%              │
│ Tokens (Today): 0 (stats may not be updated yet)        │
│                                                          │
│ Cost (Today):  $0.00                                     │
│ Cost (Month):  $0.35                                     │
└──────────────────────────────────────────────────────────┘
```

**Keyboard Shortcuts:**
- `Q` - Quit
- `R` - Refresh now
- `D` - Details (coming soon)

### 2. Detailed Statistics
```bash
# View comprehensive statistics
python3 show_stats.py
```

Output shows:
- Current status (active sessions, processes)
- Usage by time period (today/month/all-time)
- Breakdown by model (Sonnet/Haiku/Opus)
- Total costs and token counts

### 3. Quick Test
```bash
# Run non-interactive test
python3 test_mvp.py
```

## What You'll See

### Real Data from Your System
Based on your `~/.claude/stats-cache.json`:

- **Current Status**: 1 Claude Code process (PID 54430, 451 MB, 10.6 hrs uptime)
- **This Month**: 320,098 tokens → $0.35
- **All Time**: 1,369,674 tokens → $15.08
  - 190 sessions
  - 8,434 messages
  - Models: Sonnet 4.5 (1M+ tokens), Haiku 4.5 (315K tokens)

### Data Sources

Agent Monitor reads from:
- **Process info**: via `psutil` (real-time)
- **Usage stats**: `~/.claude/stats-cache.json` (updated by Claude Code)
- **Pricing**: Built-in Claude pricing table
- **Codex quota (beta)**: `/usage` API via Codex auth (`~/.codex/auth.json`)
- **Cursor usage (unstable)**: private dashboard API using `CURSOR_DASHBOARD_COOKIE` (subject to change)

**Note**: Today's usage may show as $0 if `stats-cache.json` hasn't been updated yet (last update: check file date).

### Cursor dashboard usage (unstable)
Cursor usage/cost data is fetched from private dashboard endpoints. This requires a valid
session cookie and may break if Cursor changes their backend.

**Manual setup (do not commit it):**

```bash
export CURSOR_DASHBOARD_COOKIE="WorkosCursorSessionToken=...; ..."
```

If the dashboard returns empty usage with a valid cookie (rare), you can allow zeros:

```bash
export CURSOR_ALLOW_ZERO_USAGE=1
```

If the usage endpoint still returns `{}`, set the start date from the dashboard request:

```bash
export CURSOR_USAGE_START_MS=1767763069000
```

## Architecture

```
agent-monitor/
├── agent_monitor/
│   ├── core/              # Data models & constants
│   ├── monitors/          # Process & usage monitoring
│   ├── parsers/           # Stats file parsing
│   └── ui/                # Textual TUI
├── test_mvp.py           # Quick test
├── show_stats.py         # Detailed stats
└── run_tui.sh            # TUI launcher
```

## Key Files

- **CLAUDE_CODE_TRACKING_ANALYSIS.md**: How Claude Code tracks usage internally
- **PROJECT_PLAN.md**: Full technical plan and roadmap
- **QUICKSTART.md**: Quick start guide
- **MVP_SUMMARY.md**: MVP completion summary

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black agent_monitor/
ruff check agent_monitor/
```

## Roadmap

### ✅ Phase 1: MVP (COMPLETE)
- [x] Process monitoring (Claude Code, Cursor)
- [x] Stats parsing (`stats-cache.json`)
- [x] Token usage & cost tracking
- [x] Real-time TUI

### 🚧 Phase 2: Multi-Agent (Next)
- [x] Cursor usage stats (dashboard API, unstable)
- [ ] Copilot monitoring
- [ ] Configuration system (YAML)
- [ ] Multiple panels in TUI

### 📋 Phase 3: Advanced Features
- [ ] Historical data (SQLite)
- [ ] Timeline charts
- [ ] Alerts (quota warnings)
- [ ] Export (CSV/JSON)

### 🚀 Phase 4: Release
- [ ] Full test coverage
- [ ] Cross-platform (Linux/Windows)
- [ ] PyPI package
- [ ] Documentation

## Known Limitations

1. **Stats Delay**: `stats-cache.json` may not update in real-time
2. **Today's Data**: May show $0 if stats file is stale
3. **Token Estimation**: Input/output split is estimated (70/30 ratio) for daily data
4. **Active Sessions**: Based on running processes, not session file timestamps
5. **No Quota Tracking**: Claude's API doesn't expose quota information

## Troubleshooting

### No processes detected
```bash
# Check if Claude Code is running
ps aux | grep claude

# Verify process detection
python3 test_mvp.py
```

### No usage data
```bash
# Check stats file exists
ls -la ~/.claude/stats-cache.json

# View file contents
python3 show_stats.py
```

### TUI not starting
```bash
# Test imports
python3 -c "from agent_monitor.ui.app import AgentMonitorApp"

# Check dependencies
pip install -e .
```

## Contributing

Contributions welcome! Areas of interest:

1. **New agents**: Cursor, Copilot, Codex monitoring
2. **Cross-platform**: Windows/Linux testing
3. **UI enhancements**: Charts, themes, layouts
4. **Documentation**: Tutorials, examples

## License

MIT License - See LICENSE file

## Acknowledgments

- Built with [Textual](https://github.com/Textualize/textual) for TUI
- Inspired by [nvtop](https://github.com/Syllo/nvtop) for GPU monitoring
- Process monitoring via [psutil](https://github.com/giampaolo/psutil)

---

**Made with ❤️ for AI coding productivity**
