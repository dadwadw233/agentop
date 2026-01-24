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
