# PRD: OpenCode 进程跟踪和 Token 统计功能

**文档版本**: 1.0  
**创建日期**: 2026-01-24  
**作者**: Agent Monitor Team  
**状态**: Draft

---

## 1. 概述

### 1.1 背景
Agentop 目前支持 Claude Code、Codex 和 Antigravity 的监控。OpenCode 作为一个流行的 AI 编程助手，具有多 agent 架构（Sisyphus、Atlas、Oracle 等）和多模型支持（Anthropic、OpenAI、Google、智谱等），需要专门的监控支持。

### 1.2 目标
为 Agentop 添加 OpenCode 监控功能，支持：
- 实时进程监控（CPU、内存、运行时间）
- 实时和历史 token 使用统计
- 多维度数据聚合（会话、项目、模型、agent、时间）
- TUI 界面展示

### 1.3 非目标
- 不计算成本估算（仅显示 token 数量）
- 不修改 OpenCode 本身的行为
- 不支持远程 OpenCode 实例监控

---

## 2. 数据源分析

### 2.1 进程识别

**进程特征**:
- **进程名**: `opencode`
- **可执行文件路径**: 
  - macOS: `/opt/homebrew/Cellar/opencode/*/libexec/lib/node_modules/opencode-ai/node_modules/opencode-darwin-arm64/bin/opencode`
  - Linux: 待确认
- **命令行模式**:
  - CLI 模式: `opencode` (直接运行)
  - Server 模式: `opencode serve --hostname 127.0.0.1 --port XXXX`
  - LSP 模式: `opencode run /path/to/langserver.js --stdio`

**检测策略**:
```python
AGENT_PATTERNS = {
    AgentType.OPENCODE: {
        "process_names": ["opencode"],
        "cmdline_patterns": [
            r"opencode-darwin-arm64/bin/opencode",
            r"opencode-linux-x64/bin/opencode",
            r"(?:^|/)opencode(?:\s|$)",
        ],
        "min_memory_mb": 50,
    }
}
```

### 2.2 Token 统计数据源

#### 2.2.1 消息存储结构
**路径**: `~/.local/share/opencode/storage/message/`

**目录结构**:
```
~/.local/share/opencode/storage/
├── message/
│   ├── ses_<session-id>/
│   │   ├── msg_<message-id>.json  # 每条消息的元数据
│   │   └── ...
│   └── ...
├── session/
│   ├── global/                     # 全局会话
│   │   └── ses_<session-id>.json
│   └── <project-hash>/             # 项目级会话
│       └── ses_<session-id>.json
├── part/                           # 消息内容片段
│   └── msg_<message-id>/
│       └── prt_<part-id>.json
└── ...
```

#### 2.2.2 消息 JSON 结构
**文件**: `~/.local/share/opencode/storage/message/ses_*/msg_*.json`

```json
{
  "id": "msg_beb0772b5001t5MLvYh1AuSI5b",
  "sessionID": "ses_415013fdbffeVFCrhzsaZaztxM",
  "role": "assistant",
  "time": {
    "created": 1769174692533,
    "completed": 1769174730149
  },
  "parentID": "msg_beb0772a3001n5rjJUvWG2A1HH",
  "modelID": "glm-4.7",
  "providerID": "zai-coding-plan",
  "mode": "Sisyphus",
  "agent": "Sisyphus",
  "path": {
    "cwd": "/Users/yuyuanhong/projects/persona",
    "root": "/Users/yuyuanhong/projects/persona"
  },
  "cost": 0,
  "tokens": {
    "input": 23473,
    "output": 433,
    "reasoning": 346,
    "cache": {
      "read": 72,
      "write": 0
    }
  },
  "finish": "stop"
}
```

**关键字段**:
- `tokens.input`: 输入 token 数
- `tokens.output`: 输出 token 数
- `tokens.reasoning`: 推理 token 数（仅部分模型）
- `tokens.cache.read`: 缓存读取 token 数
- `tokens.cache.write`: 缓存写入 token 数
- `modelID`: 模型标识符
- `providerID`: 提供商标识符
- `agent`: Agent 名称（Sisyphus、Atlas、Oracle 等）
- `path.root`: 项目根目录
- `time.created` / `time.completed`: 时间戳

#### 2.2.3 会话 JSON 结构
**文件**: `~/.local/share/opencode/storage/session/*/ses_*.json`

```json
{
  "id": "ses_40fbb0e2cffe75BwFp0x6uvVp7",
  "slug": "curious-knight",
  "version": "1.1.20",
  "projectID": "global",
  "directory": "/Users/yuyuanhong/projects/coding-agent-tmp",
  "parentID": "ses_40fd72556ffeS7J4OSoL0SK747",
  "title": "Background: Search GitHub for OpenCode token tracking utilities",
  "time": {
    "created": 1769262608851,
    "updated": 1769262779274
  },
  "summary": {
    "additions": 0,
    "deletions": 0,
    "files": 0
  }
}
```

**关键字段**:
- `directory`: 项目目录路径
- `projectID`: 项目标识符（`global` 或项目 hash）
- `title`: 会话标题
- `time.created` / `time.updated`: 时间戳

### 2.3 配置文件

#### 2.3.1 模型配置
**路径**: `~/.config/opencode/opencode.json`

包含所有可用模型的定义（provider、modelID、限制等）。

#### 2.3.2 Agent 配置
**路径**: `~/.config/opencode/oh-my-opencode.json`

包含 agent 到模型的映射关系。

---

## 3. 功能需求

### 3.1 实时进程监控

**FR-1.1**: 检测所有运行中的 OpenCode 进程
- 支持 CLI、Server、LSP 等多种运行模式
- 显示进程 PID、CPU 使用率、内存占用、运行时间

**FR-1.2**: 进程分组显示
- 按运行模式分组（CLI / Server / LSP）
- 显示每个进程的工作目录

### 3.2 Token 使用统计

#### 3.2.1 实时统计
**FR-2.1**: 监控当前活跃会话的 token 使用
- 实时读取最新的消息文件
- 显示当前会话的累计 token 数
- 按 input/output/reasoning/cache 分类显示

#### 3.2.2 历史统计
**FR-2.2**: 解析历史会话数据
- 扫描 `~/.local/share/opencode/storage/message/` 下所有消息文件
- 聚合历史 token 使用数据
- 支持增量更新（仅解析新消息）

### 3.3 多维度数据聚合

**FR-3.1**: 按会话聚合
- 显示每个会话的总 token 数
- 显示会话标题、时间范围、消息数

**FR-3.2**: 按项目聚合
- 按项目目录分组统计
- 显示每个项目的总 token 数
- 区分 global 会话和项目会话

**FR-3.3**: 按模型聚合
- 按 `providerID/modelID` 分组统计
- 显示每个模型的使用次数和 token 数
- 示例：`anthropic/claude-sonnet-4-5`, `openai/gpt-5.2-codex`

**FR-3.4**: 按 Agent 聚合
- 按 agent 名称分组统计（Sisyphus、Atlas、Oracle 等）
- 显示每个 agent 的调用次数和 token 数

**FR-3.5**: 按时间聚合
- 支持时间范围过滤：今天、本周、本月、全部
- 显示时间趋势（可选：简单的文本图表）

### 3.4 TUI 界面

**FR-4.1**: OpenCode Tab
- 添加新的 "OpenCode" Tab（与 Claude Code、Codex 并列）

**FR-4.2**: 子视图切换
在 OpenCode Tab 内支持多个子视图：
1. **Overview（概览）**: 实时进程 + 今日统计摘要
2. **Sessions（会话）**: 按会话列表显示
3. **Projects（项目）**: 按项目聚合显示
4. **Models（模型）**: 按模型聚合显示
5. **Agents（代理）**: 按 agent 聚合显示
6. **Timeline（时间线）**: 按时间聚合显示

**FR-4.3**: 视图切换快捷键
- Tab 键或数字键（1-6）切换子视图
- 显示当前视图名称和快捷键提示

**FR-4.4**: 数据刷新
- 实时数据：1 秒刷新间隔
- 历史数据：首次加载 + 手动刷新（按 `r` 键）

---

## 4. 数据模型

### 4.1 核心数据结构

```python
@dataclass
class OpenCodeTokenUsage:
    """OpenCode token 使用统计"""
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    
    @property
    def total_tokens(self) -> int:
        return (self.input_tokens + self.output_tokens + 
                self.reasoning_tokens + self.cache_read_tokens + 
                self.cache_write_tokens)

@dataclass
class OpenCodeMessage:
    """OpenCode 消息元数据"""
    id: str
    session_id: str
    role: str  # "user" | "assistant"
    model_id: str
    provider_id: str
    agent: str
    project_root: str
    tokens: OpenCodeTokenUsage
    time_created: datetime
    time_completed: Optional[datetime]

@dataclass
class OpenCodeSession:
    """OpenCode 会话元数据"""
    id: str
    project_id: str
    directory: str
    title: str
    time_created: datetime
    time_updated: datetime
    message_count: int = 0
    total_tokens: OpenCodeTokenUsage = field(default_factory=OpenCodeTokenUsage)

@dataclass
class OpenCodeMetrics:
    """OpenCode 综合指标"""
    processes: List[ProcessMetrics]
    sessions: List[OpenCodeSession]
    
    # 聚合统计
    total_tokens: OpenCodeTokenUsage
    by_session: Dict[str, OpenCodeTokenUsage]
    by_project: Dict[str, OpenCodeTokenUsage]
    by_model: Dict[str, OpenCodeTokenUsage]
    by_agent: Dict[str, OpenCodeTokenUsage]
    by_date: Dict[str, OpenCodeTokenUsage]  # YYYY-MM-DD
    
    # 时间范围
    time_range: str  # "today" | "week" | "month" | "all"
```

### 4.2 数据解析器

```python
class OpenCodeStatsParser:
    """解析 OpenCode 统计数据"""
    
    def __init__(self, storage_path: Path = Path.home() / ".local/share/opencode/storage"):
        self.storage_path = storage_path
        self.message_path = storage_path / "message"
        self.session_path = storage_path / "session"
    
    def parse_message(self, message_file: Path) -> Optional[OpenCodeMessage]:
        """解析单个消息文件"""
        pass
    
    def parse_session(self, session_file: Path) -> Optional[OpenCodeSession]:
        """解析单个会话文件"""
        pass
    
    def get_all_messages(self, time_range: str = "all") -> List[OpenCodeMessage]:
        """获取所有消息（支持时间过滤）"""
        pass
    
    def get_all_sessions(self) -> List[OpenCodeSession]:
        """获取所有会话"""
        pass
    
    def aggregate_by_session(self, messages: List[OpenCodeMessage]) -> Dict[str, OpenCodeTokenUsage]:
        """按会话聚合"""
        pass
    
    def aggregate_by_project(self, messages: List[OpenCodeMessage]) -> Dict[str, OpenCodeTokenUsage]:
        """按项目聚合"""
        pass
    
    def aggregate_by_model(self, messages: List[OpenCodeMessage]) -> Dict[str, OpenCodeTokenUsage]:
        """按模型聚合"""
        pass
    
    def aggregate_by_agent(self, messages: List[OpenCodeMessage]) -> Dict[str, OpenCodeTokenUsage]:
        """按 agent 聚合"""
        pass
    
    def aggregate_by_date(self, messages: List[OpenCodeMessage]) -> Dict[str, OpenCodeTokenUsage]:
        """按日期聚合"""
        pass
```

### 4.3 进程监控器

```python
class OpenCodeMonitor:
    """OpenCode 进程和使用监控"""
    
    def __init__(self):
        self.process_monitor = ProcessMonitor()
        self.stats_parser = OpenCodeStatsParser()
    
    def get_metrics(self, time_range: str = "today") -> OpenCodeMetrics:
        """获取综合指标"""
        # 1. 获取进程信息
        processes = self.process_monitor.find_processes(AgentType.OPENCODE)
        
        # 2. 解析消息和会话
        messages = self.stats_parser.get_all_messages(time_range)
        sessions = self.stats_parser.get_all_sessions()
        
        # 3. 聚合统计
        total_tokens = self._calculate_total(messages)
        by_session = self.stats_parser.aggregate_by_session(messages)
        by_project = self.stats_parser.aggregate_by_project(messages)
        by_model = self.stats_parser.aggregate_by_model(messages)
        by_agent = self.stats_parser.aggregate_by_agent(messages)
        by_date = self.stats_parser.aggregate_by_date(messages)
        
        return OpenCodeMetrics(
            processes=processes,
            sessions=sessions,
            total_tokens=total_tokens,
            by_session=by_session,
            by_project=by_project,
            by_model=by_model,
            by_agent=by_agent,
            by_date=by_date,
            time_range=time_range
        )
```

---

## 5. UI 设计

### 5.1 Tab 结构

```
┌─────────────────────────────────────────────────────────────┐
│ Agentop - AI Agent Monitor                                  │
├─────────────────────────────────────────────────────────────┤
│ [Claude Code] [Antigravity] [Codex] [OpenCode]             │
├─────────────────────────────────────────────────────────────┤
│ OpenCode Monitor                                            │
│                                                              │
│ View: [1] Overview  [2] Sessions  [3] Projects  [4] Models │
│       [5] Agents    [6] Timeline                            │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [当前视图内容]                                           │ │
│ │                                                          │ │
│ │                                                          │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Press 1-6 to switch views | r: refresh | q: quit            │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 子视图设计

#### 5.2.1 Overview（概览）
```
┌─────────────────────────────────────────────────────────────┐
│ Overview - Today's Activity                                 │
├─────────────────────────────────────────────────────────────┤
│ Running Processes: 3                                        │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ PID    Mode      CPU    Memory   Uptime   Directory     │ │
│ │ 17217  CLI       18.5%  607 MB   0:39:18  ~/projects/.. │ │
│ │ 71516  Server    0.1%   67 MB    16:29:19 (global)      │ │
│ │ 18914  LSP       0.0%   390 MB   0:14:85  ~/projects/.. │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Token Usage (Today)                                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Input:      1,234,567 tokens                            │ │
│ │ Output:       234,567 tokens                            │ │
│ │ Reasoning:     45,678 tokens                            │ │
│ │ Cache Read:   567,890 tokens                            │ │
│ │ ─────────────────────────────                           │ │
│ │ Total:      2,082,702 tokens                            │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Top Models (Today)                                          │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ anthropic/claude-sonnet-4-5    45%  (934,215 tokens)   │ │
│ │ openai/gpt-5.2-codex           30%  (624,810 tokens)   │ │
│ │ zai-coding-plan/glm-4.7        25%  (523,677 tokens)   │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2.2 Sessions（会话）
```
┌─────────────────────────────────────────────────────────────┐
│ Sessions - All Time                                         │
├─────────────────────────────────────────────────────────────┤
│ Session ID              Title                  Tokens  Msgs │
│ ─────────────────────────────────────────────────────────── │
│ ses_40fbb0e2cffe...    Background: Search...   45,678   12  │
│ ses_40fbb1887ffe...    Fix CI pipeline         23,456    8  │
│ ses_40fbb230cffe...    Add OpenCode monitor   123,456   45  │
│ ses_40fbb2fbcffe...    Refactor parser         34,567   15  │
│ ...                                                          │
│                                                              │
│ Total: 234 sessions | 5,678,901 tokens                      │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2.3 Projects（项目）
```
┌─────────────────────────────────────────────────────────────┐
│ Projects - All Time                                         │
├─────────────────────────────────────────────────────────────┤
│ Project Directory                        Tokens    Sessions │
│ ─────────────────────────────────────────────────────────── │
│ ~/projects/agent-monitor              1,234,567         45  │
│ ~/projects/persona                      567,890         23  │
│ ~/projects/coding-agent-tmp             234,567         12  │
│ (global)                                456,789         89  │
│ ...                                                          │
│                                                              │
│ Total: 12 projects | 5,678,901 tokens                       │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2.4 Models（模型）
```
┌─────────────────────────────────────────────────────────────┐
│ Models - All Time                                           │
├─────────────────────────────────────────────────────────────┤
│ Provider/Model                           Tokens    Messages │
│ ─────────────────────────────────────────────────────────── │
│ anthropic/claude-sonnet-4-5           2,345,678       1,234 │
│ openai/gpt-5.2-codex                  1,234,567         678 │
│ zai-coding-plan/glm-4.7               1,098,765       2,345 │
│ google/antigravity-gemini-3-pro-high    567,890         234 │
│ ...                                                          │
│                                                              │
│ Total: 8 models | 5,678,901 tokens                          │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2.5 Agents（代理）
```
┌─────────────────────────────────────────────────────────────┐
│ Agents - All Time                                           │
├─────────────────────────────────────────────────────────────┤
│ Agent Name              Tokens      Messages   Avg/Message  │
│ ─────────────────────────────────────────────────────────── │
│ Sisyphus             2,345,678         1,234        1,901   │
│ Atlas                1,234,567           678        1,821   │
│ Oracle                 567,890           234        2,427   │
│ librarian              456,789           890          513   │
│ explore                234,567         1,234          190   │
│ ...                                                          │
│                                                              │
│ Total: 12 agents | 5,678,901 tokens                         │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2.6 Timeline（时间线）
```
┌─────────────────────────────────────────────────────────────┐
│ Timeline - Last 7 Days                                      │
├─────────────────────────────────────────────────────────────┤
│ Date         Input      Output    Reasoning   Cache   Total │
│ ─────────────────────────────────────────────────────────── │
│ 2026-01-24  123,456    23,456      4,567    56,789  208,268│
│ 2026-01-23  234,567    34,567      5,678    67,890  342,702│
│ 2026-01-22  345,678    45,678      6,789    78,901  477,046│
│ 2026-01-21  456,789    56,789      7,890    89,012  610,480│
│ ...                                                          │
│                                                              │
│ Time Range: [t] Today  [w] Week  [m] Month  [a] All         │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. 技术实现

### 6.1 文件结构

```
agentop/
├── core/
│   ├── models.py              # 添加 OpenCode 数据模型
│   └── constants.py           # 添加 OpenCode 常量
├── monitors/
│   └── opencode.py            # OpenCodeMonitor
├── parsers/
│   └── opencode_stats.py      # OpenCodeStatsParser
└── ui/
    └── widgets/
        └── opencode_panel.py  # OpenCodePanel (TUI)
```

### 6.2 依赖项

无新增依赖，使用现有的：
- `psutil`: 进程监控
- `pydantic`: 数据验证
- `textual`: TUI 框架
- `rich`: 格式化输出

### 6.3 性能考虑

**挑战**: 历史消息文件可能非常多（数千个会话，数万条消息）

**优化策略**:
1. **增量解析**: 缓存已解析的消息，仅解析新文件
2. **索引文件**: 维护一个索引文件（`~/.cache/agentop/opencode-index.json`）
   ```json
   {
     "last_scan": "2026-01-24T22:00:00Z",
     "message_count": 12345,
     "session_count": 234,
     "aggregates": {
       "by_session": {...},
       "by_project": {...},
       "by_model": {...},
       "by_agent": {...},
       "by_date": {...}
     }
   }
   ```
3. **懒加载**: 仅在切换到历史视图时才解析历史数据
4. **时间过滤**: 默认仅加载最近 30 天的数据，提供"加载全部"选项
5. **并发解析**: 使用多线程/多进程解析消息文件

### 6.4 错误处理

- **文件不存在**: 优雅降级，显示"No data available"
- **JSON 解析失败**: 跳过损坏的文件，记录警告
- **权限问题**: 显示错误提示，建议检查文件权限
- **版本兼容性**: 检测 OpenCode 版本，警告不兼容的数据格式

---

## 7. 测试计划

### 7.1 单元测试

- `test_opencode_stats_parser.py`: 测试消息/会话解析
- `test_opencode_monitor.py`: 测试进程检测和指标聚合
- `test_opencode_aggregation.py`: 测试各维度聚合逻辑

### 7.2 集成测试

- 使用真实的 OpenCode 数据目录进行测试
- 验证多种场景：
  - 空数据（首次运行）
  - 少量数据（< 10 会话）
  - 大量数据（> 1000 会话）
  - 多项目场景
  - 多模型场景

### 7.3 性能测试

- 测试解析 10,000 条消息的时间
- 测试 TUI 刷新性能（1 秒间隔）
- 测试内存占用（大数据集）

---

## 8. 发布计划

### 8.1 阶段 1: MVP（最小可行产品）
**目标**: 基础功能可用

**功能**:
- ✅ 进程检测和监控
- ✅ 实时 token 统计（当前会话）
- ✅ Overview 视图
- ✅ Sessions 视图

**时间**: 1-2 周

### 8.2 阶段 2: 多维度聚合
**目标**: 完整的历史统计

**功能**:
- ✅ 历史数据解析
- ✅ Projects、Models、Agents、Timeline 视图
- ✅ 时间范围过滤

**时间**: 1 周

### 8.3 阶段 3: 性能优化
**目标**: 处理大数据集

**功能**:
- ✅ 增量解析和索引
- ✅ 并发优化
- ✅ 内存优化

**时间**: 1 周

### 8.4 阶段 4: 完善和发布
**目标**: 生产就绪

**功能**:
- ✅ 完整测试覆盖
- ✅ 文档更新
- ✅ 错误处理完善
- ✅ 发布到 PyPI

**时间**: 1 周

---

## 9. 未来扩展

### 9.1 成本计算（可选）
如果未来需要成本估算：
- 支持用户自定义定价配置文件
- 从 OpenCode 配置读取模型信息
- 集成公开的模型定价 API

### 9.2 导出功能
- 导出统计数据为 CSV/JSON
- 生成使用报告（Markdown/HTML）

### 9.3 告警功能
- Token 使用超过阈值时告警
- 异常高频调用检测

### 9.4 可视化增强
- 简单的 ASCII 图表（token 趋势）
- 可选的 Web 界面（使用 Textual Web）

---

## 10. 风险和缓解

### 10.1 数据格式变更
**风险**: OpenCode 更新可能改变数据格式

**缓解**:
- 版本检测和兼容性处理
- 优雅降级，显示警告
- 社区反馈机制

### 10.2 性能问题
**风险**: 大量历史数据导致解析缓慢

**缓解**:
- 增量解析和缓存
- 时间范围限制
- 异步加载

### 10.3 跨平台兼容性
**风险**: Linux/Windows 路径和进程检测差异

**缓解**:
- 使用 `pathlib` 处理路径
- 测试多平台场景
- 社区贡献和反馈

---

## 11. 成功指标

- ✅ 能够检测所有运行中的 OpenCode 进程
- ✅ 准确解析 95%+ 的消息文件
- ✅ 历史数据解析时间 < 5 秒（1000 条消息）
- ✅ TUI 刷新流畅（无卡顿）
- ✅ 用户反馈积极（GitHub issues/discussions）

---

## 12. 参考资料

### 12.1 OpenCode 数据源
- 消息存储: `~/.local/share/opencode/storage/message/`
- 会话存储: `~/.local/share/opencode/storage/session/`
- 配置文件: `~/.config/opencode/`

### 12.2 现有实现参考
- Claude Code 监控: `agentop/monitors/claude_code.py`
- Codex 监控: `agentop/monitors/codex.py`
- TUI 面板: `agentop/ui/widgets/agent_panel.py`

---

**文档结束**
