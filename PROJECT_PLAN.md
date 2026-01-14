# Agent Monitor - 项目构建方案

## 项目概述

Agent Monitor 是一个类似 nvtop 的终端 UI 工具，用于实时监控本地运行的 AI coding agent 工具（Claude Code、Cursor、Copilot、Codex 等）的进程状态和资源使用情况。

## 核心目标

- **实时监控**：本地 agent 进程的 CPU、内存、运行时长
- **Quota 追踪**：API 使用量、Token 消耗、费用估算
- **会话管理**：活跃会话数量、历史记录
- **告警系统**：资源/配额预警

## 技术栈选择

### 推荐方案：Python + Rich/Textual

**为什么选择 Python？**
1. **快速开发**：更适合 MVP 快速验证
2. **丰富生态**：`psutil`（进程监控）、`rich`/`textual`（TUI）成熟可靠
3. **易于扩展**：解析 JSON/JSONL 日志非常方便
4. **跨平台**：Python 在 macOS/Linux/Windows 都有良好支持

**核心依赖**
```python
# 进程监控
psutil==6.1.0          # 跨平台进程/系统信息

# TUI 框架
textual==0.88.0        # 现代 TUI 框架
rich==13.9.0           # 美化输出

# 数据处理
pydantic==2.10.0       # 数据验证
aiofiles==24.1.0       # 异步文件操作
httpx==0.28.0          # 异步 HTTP 客户端

# 配置管理
pyyaml==6.0.2          # YAML 配置
platformdirs==4.3.0    # 跨平台目录
```

## 项目架构

```
agent-monitor/
├── agent_monitor/
│   ├── __init__.py
│   ├── __main__.py              # 入口点
│   │
│   ├── core/                    # 核心模块
│   │   ├── __init__.py
│   │   ├── config.py           # 配置管理
│   │   ├── models.py           # 数据模型
│   │   └── constants.py        # 常量定义
│   │
│   ├── monitors/                # 监控模块
│   │   ├── __init__.py
│   │   ├── base.py             # 基础监控类
│   │   ├── process.py          # 进程监控
│   │   ├── claude_code.py      # Claude Code 专用
│   │   ├── cursor.py           # Cursor 专用
│   │   ├── copilot.py          # GitHub Copilot
│   │   └── codex.py            # OpenAI Codex
│   │
│   ├── parsers/                 # 日志解析
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── claude_logs.py      # Claude Code JSONL
│   │   └── cursor_logs.py      # Cursor 日志
│   │
│   ├── api/                     # API 客户端
│   │   ├── __init__.py
│   │   ├── anthropic.py        # Anthropic API
│   │   ├── openai.py           # OpenAI API
│   │   └── cache.py            # API 缓存
│   │
│   ├── storage/                 # 数据存储
│   │   ├── __init__.py
│   │   ├── db.py               # SQLite 存储
│   │   └── history.py          # 历史数据
│   │
│   └── ui/                      # 界面
│       ├── __init__.py
│       ├── app.py              # 主应用
│       ├── dashboard.py        # 仪表盘
│       ├── widgets/            # UI 组件
│       │   ├── __init__.py
│       │   ├── process_list.py
│       │   ├── quota_panel.py
│       │   ├── timeline.py
│       │   └── alerts.py
│       └── theme.py            # 主题配置
│
├── config/
│   ├── agents.yaml             # Agent 配置
│   └── settings.yaml           # 全局设置
│
├── tests/
│   ├── test_monitors.py
│   ├── test_parsers.py
│   └── fixtures/
│
├── pyproject.toml
├── README.md
└── LICENSE
```

## 核心功能设计

### 1. 进程监控器（monitors/process.py）

**检测逻辑**
```python
# 已知 agent 进程特征（基于你的系统）
AGENT_PATTERNS = {
    'claude_code': {
        'process_names': ['claude'],
        'cmdline_patterns': [
            r'\.local/bin/claude',
            r'--model\s+claude-',
        ],
        'min_memory_mb': 50,  # 最小内存阈值
    },
    'cursor': {
        'process_names': ['Cursor', 'Cursor Helper'],
        'cmdline_patterns': [
            r'/Applications/Cursor\.app',
            r'Cursor Helper \(Renderer\)',
        ],
        'min_memory_mb': 100,
    },
    'copilot': {
        'process_names': ['copilot-agent'],
        'cmdline_patterns': [r'copilot'],
    },
}
```

**采集指标**
```python
@dataclass
class ProcessMetrics:
    pid: int
    name: str
    cmdline: str
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    num_threads: int
    create_time: datetime
    status: str  # running, sleeping, zombie
```

### 2. Claude Code 监控器（monitors/claude_code.py）

**数据源**
```python
# 本地日志路径
CLAUDE_LOGS = {
    'sessions': '~/.claude-code/sessions/',
    'settings': '~/.claude-code/settings.json',
    'usage_cache': '~/.claude-code/usage.db',
}
```

**监控内容**
```python
@dataclass
class ClaudeCodeMetrics:
    # 进程信息
    processes: List[ProcessMetrics]

    # 会话信息
    active_sessions: int
    total_sessions_today: int

    # Token 使用（从 JSONL 解析）
    tokens_input_today: int
    tokens_output_today: int
    tokens_total_today: int

    # 配额（如果有 API）
    quota_limit: Optional[int]
    quota_used: Optional[int]
    quota_percent: Optional[float]

    # 费用估算
    cost_today: float
    cost_this_month: float

    # 最后活动
    last_active: datetime
```

### 3. Cursor 监控器（monitors/cursor.py）

**检测策略**
```python
# Cursor 有多个子进程
CURSOR_PROCESS_TYPES = {
    'main': r'/Applications/Cursor\.app/Contents/MacOS/Cursor$',
    'gpu': r'Cursor Helper \(GPU\)',
    'renderer': r'Cursor Helper \(Renderer\)',
    'plugin': r'Cursor Helper \(Plugin\)',
    'shared': r'Cursor Helper: shared-process',
}
```

**监控内容**
```python
@dataclass
class CursorMetrics:
    # 进程组
    main_process: Optional[ProcessMetrics]
    helper_processes: List[ProcessMetrics]
    total_cpu: float
    total_memory_mb: float

    # 工作区信息（从日志推断）
    active_workspaces: int

    # API 使用（如果可获取）
    api_calls_today: Optional[int]

    # 费用
    cost_estimate: Optional[float]
```

### 4. 日志解析器（parsers/claude_logs.py）

**Claude Code JSONL 格式**
```python
class ClaudeLogParser:
    """解析 Claude Code 的 JSONL 会话日志"""

    def parse_session_file(self, path: Path) -> SessionData:
        """
        解析单个会话文件
        格式示例：
        {"type": "request", "timestamp": "...", "model": "claude-sonnet-4-5", ...}
        {"type": "response", "tokens": {"input": 1234, "output": 567}, ...}
        """
        with open(path) as f:
            for line in f:
                entry = json.loads(line)
                if entry['type'] == 'response':
                    self.extract_tokens(entry)
                    self.extract_cost(entry)

    def get_today_usage(self) -> UsageStats:
        """聚合今日所有会话的使用量"""
        sessions = self.list_sessions(date=today())
        return sum(self.parse_session_file(s) for s in sessions)
```

### 5. UI 设计（ui/dashboard.py）

**布局结构**
```
┌─ Agent Monitor ─────────────────────────────────────────────────────┐
│ 🟢 3 agents running | ⏱ Uptime: 2h 34m | 💾 Cache: 1.2GB          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ ┌─ CLAUDE CODE ──────────────────────────────── 🟢 Active ─────┐  │
│ │ Processes:  2 (claude x2)                                      │  │
│ │ CPU:        3.2%  ████░░░░░░░░░░░░░░░░░░░░░░░░                 │  │
│ │ Memory:     890 MB                                              │  │
│ │ Sessions:   2 active • 12 today                                 │  │
│ │                                                                  │  │
│ │ Token Usage (Today)                                             │  │
│ │   Input:   145,892  ██████████████░░░░░░░░ 73%                 │  │
│ │   Output:   54,231  █████░░░░░░░░░░░░░░░░░ 27%                 │  │
│ │   Total:   200,123 / 200,000 limit                             │  │
│ │   ⚠️  Warning: Near quota limit!                                │  │
│ │                                                                  │  │
│ │ Cost Estimate:  $4.23 today • $87.45 this month                │  │
│ └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│ ┌─ CURSOR ───────────────────────────────────── 🟢 Active ─────┐  │
│ │ Processes:  8 (main + 7 helpers)                               │  │
│ │ CPU:        4.8%  ██████░░░░░░░░░░░░░░░░░░░░░                  │  │
│ │ Memory:     1.2 GB                                              │  │
│ │ Workspaces: 1                                                   │  │
│ │ Cost:       ~$2.50 today (estimated)                           │  │
│ └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│ ┌─ Token Usage Timeline (Last 24h) ─────────────────────────────┐  │
│ │     ┌──────────────────────────────────────────────┐           │  │
│ │ 25K │                                     ╭╮        │           │  │
│ │ 20K │                                    ╭╯╰╮       │           │  │
│ │ 15K │         ╭╮                    ╭╮  │  │       │           │  │
│ │ 10K │    ╭╮  ╭╯╰╮  ╭╮    ╭╮       ╭╯│ ╭╯  │       │           │  │
│ │  5K │╭╮╭╮││  │  │ ╭╯╰╮  ╭╯╰╮     ╭╯ │╭╯   │╮      │           │  │
│ │     └─┴┴┴┴┴┴──┴──┴─┴──┴──┴──┴─────┴──┴┴────┴┴──────┘           │  │
│ │      0   4   8  12  16  20  24h                                │  │
│ └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│ [Q]uit  [R]efresh  [F]ilter  [D]etails  [S]ettings  [?]Help       │
└─────────────────────────────────────────────────────────────────────┘
```

**Textual 实现示例**
```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import Container, Vertical

class AgentMonitorApp(App):
    """Agent Monitor TUI Application"""

    CSS = """
    .agent-panel {
        border: solid $primary;
        padding: 1;
        margin: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            ClaudeCodePanel(id="claude"),
            CursorPanel(id="cursor"),
            TimelineWidget(id="timeline"),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_data)

    async def refresh_data(self) -> None:
        # 更新所有监控数据
        await self.query_one("#claude").update()
        await self.query_one("#cursor").update()
```

## 配置系统

### agents.yaml
```yaml
# Agent 配置
agents:
  claude_code:
    enabled: true
    display_name: "Claude Code"
    icon: "🤖"

    # 进程识别
    process:
      names: ["claude"]
      cmdline_patterns:
        - "\.local/bin/claude"
        - "--model\\s+claude-"
      min_memory_mb: 50

    # 数据源
    data_sources:
      # 本地日志（优先）
      logs:
        sessions_dir: "~/.claude-code/sessions/"
        format: "jsonl"

      # API（如果配置）
      api:
        enabled: false
        base_url: "https://api.anthropic.com/v1"
        key_env: "ANTHROPIC_API_KEY"

    # 监控配置
    monitoring:
      track_tokens: true
      track_cost: true
      estimate_pricing:
        input_per_1m: 3.0   # USD per 1M tokens
        output_per_1m: 15.0

    # 告警
    alerts:
      token_threshold: 0.9  # 90% 告警
      cost_daily_limit: 10.0  # USD

  cursor:
    enabled: true
    display_name: "Cursor"
    icon: "💡"

    process:
      names: ["Cursor", "Cursor Helper"]
      cmdline_patterns:
        - "/Applications/Cursor\\.app"
      group_by_type: true  # 分组显示子进程

    monitoring:
      track_tokens: false  # Cursor 没有直接 token 信息
      track_workspaces: true
```

### settings.yaml
```yaml
# 全局设置
monitor:
  refresh_interval: 1.0  # 秒
  cache_ttl: 300  # API 缓存 5 分钟
  history_retention_days: 30

ui:
  theme: "dark"  # dark | light
  show_sparklines: true
  compact_mode: false

storage:
  database_path: "~/.agent-monitor/data.db"
  max_size_mb: 100

logging:
  level: "INFO"
  file: "~/.agent-monitor/logs/monitor.log"
```

## 数据存储（SQLite）

**Schema**
```sql
-- 进程历史记录
CREATE TABLE process_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    agent_type TEXT NOT NULL,
    pid INTEGER NOT NULL,
    cpu_percent REAL,
    memory_mb REAL,
    status TEXT
);

-- Token 使用记录
CREATE TABLE token_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    agent_type TEXT NOT NULL,
    session_id TEXT,
    model TEXT,
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost REAL
);

-- 告警记录
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    agent_type TEXT NOT NULL,
    alert_type TEXT,  -- quota_warning, cost_limit, etc.
    message TEXT,
    acknowledged BOOLEAN DEFAULT FALSE
);
```

## 实现路线图

### Phase 1: MVP (1-2 周)
- [ ] 项目初始化 + 依赖配置
- [ ] 基础进程监控（psutil）
- [ ] Claude Code 日志解析（JSONL）
- [ ] 简单 TUI 界面（Textual）
- [ ] 实时刷新机制

**目标输出**：可以监控 Claude Code 进程和基本 token 使用

### Phase 2: 多 Agent 支持 (1-2 周)
- [ ] Cursor 监控
- [ ] Copilot 监控（如果需要）
- [ ] 配置系统（YAML）
- [ ] 进程分组显示
- [ ] UI 优化（面板、主题）

### Phase 3: 高级功能 (1 周)
- [ ] SQLite 历史存储
- [ ] Timeline 图表（sparkline）
- [ ] 告警系统
- [ ] 快捷键操作
- [ ] 详情视图（按 D 查看）

### Phase 4: 完善与发布 (1 周)
- [ ] 单元测试
- [ ] 跨平台测试（macOS/Linux）
- [ ] 打包（PyPI）
- [ ] 文档（README + Wiki）

## 快速开始示例

**安装**
```bash
# 从 PyPI 安装（未来）
pip install agent-monitor

# 或者从源码
git clone https://github.com/yourusername/agent-monitor.git
cd agent-monitor
pip install -e .
```

**使用**
```bash
# 基本使用
agent-monitor

# 指定配置
agent-monitor --config ~/.agent-monitor/config.yaml

# 仅监控特定 agent
agent-monitor --agents claude_code,cursor

# 紧凑模式
agent-monitor --compact
```

## 技术挑战与解决方案

### 1. 进程识别准确性
**挑战**：不同版本、安装方式的进程特征不同
**方案**：
- 多特征匹配（进程名 + 命令行 + 内存阈值）
- 用户自定义规则（agents.yaml）
- 启发式学习（记录用户确认的进程）

### 2. 日志格式变化
**挑战**：Claude Code 等工具的日志格式可能更新
**方案**：
- 版本检测 + 多格式解析器
- 容错机制（字段缺失时降级）
- 社区维护格式库

### 3. API 限流
**挑战**：频繁调用 Anthropic/OpenAI API 可能被限流
**方案**：
- 本地优先（优先解析日志）
- 智能缓存（5-30 分钟 TTL）
- 可选功能（用户决定是否启用 API）

### 4. 性能开销
**挑战**：监控工具本身不应占用太多资源
**方案**：
- 异步架构（不阻塞 UI）
- 采样频率可配置（默认 1 秒）
- 懒加载（仅加载可见数据）

## 与现有工具对比

| 工具 | 类型 | 优势 | 劣势 |
|------|------|------|------|
| ccusage | CLI | 历史分析强 | 无实时监控、无进程监控 |
| AgentOps | Web Dashboard | 功能全面 | 需要集成、非本地 |
| nvtop | TUI | 实时性好 | GPU 专用 |
| **Agent Monitor** | TUI | **本地实时 + 多 agent + 进程监控** | 新项目、需要构建 |

## 后续扩展方向

1. **Web Dashboard**：Textual 支持 web 模式，可以浏览器访问
2. **导出报告**：生成 CSV/JSON/HTML 报告
3. **集成 MCP**：通过 MCP 协议扩展监控能力
4. **团队模式**：聚合多个开发者的使用情况
5. **插件系统**：支持自定义 agent 监控器

## 下一步行动

我建议立即开始 **Phase 1 MVP** 的实现，重点是：

1. **搭建项目骨架**：创建目录结构、pyproject.toml
2. **实现核心监控**：`monitors/process.py` + `monitors/claude_code.py`
3. **基础 UI**：使用 Textual 创建简单仪表盘
4. **验证可行性**：确保能正确识别进程和解析日志

你希望我现在开始实现吗？我可以帮你：
- 创建完整的项目结构
- 实现第一个可运行的 MVP
- 配置开发环境（pyproject.toml、依赖等）
