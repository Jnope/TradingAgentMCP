# TradingAgentsMCP 重构方案 PRD

## 1. 项目概述

### 1.1 背景

../TradingAgents为原始 TradingAgents 框架；
当前项目 `TradingAgentsMCP` 是基于原始 TradingAgents 框架的 MCP 封装，数据源以 yfinance、alpha_vantage、finnhub 等海外数据源为主，仅适用于美股分析。需参考 `TradingAgents-MCP` 项目的架构，将当前项目重构为面向 A 股的 FastMCP 服务。

### 1.2 目标

- 将项目重构为 **FastMCP 服务**，对外暴露单分析师工具、`trading_agent` 全流程工具和 `health_check` 方法
- 数据源替换为 **timelyre（内部数据库）** + **akshare（新闻和舆情）**，仅用于 A 股分析
- 保留当前项目的分析流程逻辑（LangGraph 多 Agent 协作 → 多空辩论 → 风险评估 → 交易决策）
- 日志和缓存统一存储于 `~/.tradingagents`，日志每天滚动保留 7 天
- 环境变量配置 LLM 相关参数，参考参考项目的 `MCP_*` 前缀体系

### 1.3 约束

- 仅支持 A 股，移除美股/港股相关数据源和逻辑
- 暂不做数据查询降级（timelyre 不可用时直接报错，不降级到 tushare/baostock）
- 保留 LangGraph 多 Agent 协作流程不变

---

## 2. 当前架构分析

### 2.1 当前项目结构

```
TradingAgentsMCP/
├── main.py                    # 本地测试入口
├── mcp/
│   ├── __init__.py
│   └── main.py                # 当前 MCP 入口（stdio/http）
├── tradingagents/
│   ├── __init__.py
│   ├── default_config.py      # 默认配置 + 环境变量覆盖
│   ├── agents/
│   │   ├── analysts/          # 4 个分析师（market/fundamentals/news/sentiment）
│   │   ├── managers/          # research_manager / risk_manager
│   │   ├── researchers/       # bull / bear
│   │   ├── risk_mgmt/         # aggressive / conservative / neutral debator
│   │   ├── trader/            # trader
│   │   ├── schemas.py         # Pydantic 结构化输出模型
│   │   └── utils/             # agent_utils / agent_states / memory / tools
│   ├── dataflows/             # 数据接口层（以 yfinance/finnhub 为主）
│   │   ├── interface.py       # 统一数据入口
│   │   ├── config.py
│   │   ├── y_finance.py
│   │   ├── alpha_vantage*.py
│   │   └── ...
│   ├── graph/                 # LangGraph 编排
│   │   ├── trading_graph.py   # 核心图
│   │   ├── setup.py           # 图构建
│   │   ├── propagation.py     # 执行
│   │   └── ...
│   └── llm_clients/           # LLM 客户端工厂
│       ├── factory.py
│       ├── openai_client.py
│       └── ...
├── pyproject.toml
└── .env.example
```

### 2.2 关键问题

1. **数据源不匹配**：当前 dataflows 以 yfinance/finnhub/alpha_vantage 为主，不适合 A 股
2. **MCP 层简陋**：`mcp/main.py` 仅有启动逻辑，无 FastMCP Tool 定义
3. **无单分析师调用**：缺少独立调用单个分析师的能力
4. **无健康检查**：缺少 agent_status/health_check 工具
5. **日志未统一**：日志分散，未统一到 `~/.tradingagents`，无滚动策略

---

## 3. 参考项目架构（TradingAgents-MCP）

### 3.1 关键设计模式

| 模块 | 参考项目实现 | 说明 |
|------|-------------|------|
| MCP Server | `tradingagents_mcp/server.py` | FastMCP 工具注册（@mcp.tool） |
| 入口 | `tradingagents_mcp/__main__.py` | stdio/http/check 三种模式 |
| 共享上下文 | `tradingagents_mcp/shared_context.py` | 进程级 LLM+Toolkit 单例 |
| 配置构建 | `tradingagents_mcp/validators.py` | build_config/validate_symbol/nearest_trade_date |
| 单分析师 | `_run_single_analyst()` | 复用 create_xxx_analyst + Toolkit |
| 数据源 | `dataflows/providers/china/internal.py` | timelyre 内部数据库 |
| 基本面 | `dataflows/providers/china/internal_fundamentals_data.py` | 三大报表格式化 |
| SQL 查询 | `dataflows/providers/china/internal_queries.py` | timelyre DatabaseConn 封装 |
| 新闻/舆情 | akshare | 统一新闻工具 |

### 3.2 MCP Tool 清单（参考项目）

| Tool | 功能 |
|------|------|
| `trading_agent` | 完整全流程分析 |
| `market_analyst` | 独立市场/技术分析 |
| `fundamentals_analyst` | 独立基本面分析 |
| `news_analyst` | 独立新闻分析 |
| `social_analyst` | 独立社交情绪分析 |
| `compare_stocks` | 多股对比分析 |
| `batch_analyze` | 批量独立分析 |
| `period_compare` | 历史区间对比 |
| `screen_stocks` | 股票筛选 |
| `agent_status` | 健康检查 |

---

## 4. 重构方案

### 4.1 目标项目结构

```
TradingAgentsMCP/
├── tradingagents_mcp/               # 新增：MCP 服务包
│   ├── __init__.py
│   ├── __main__.py                  # 入口：stdio / http / check
│   ├── server.py                    # FastMCP 工具注册
│   ├── shared_context.py            # 进程级 LLM + Toolkit 单例
│   ├── validators.py                # 参数校验 + 配置构建
│   ├── trade_calendar.py            # A 股交易日历
│   └── prompts.py                   # MCP Prompts（可选）
├── tradingagents/
│   ├── __init__.py
│   ├── default_config.py            # 重构：仅 A 股配置，MCP_* 环境变量
│   ├── agents/                      # 保留：分析流程不变
│   │   ├── analysts/
│   │   ├── managers/
│   │   ├── researchers/
│   │   ├── risk_mgmt/
│   │   ├── trader/
│   │   ├── schemas.py
│   │   └── utils/
│   │       ├── agent_utils.py       # 重构：Toolkit 替换为 A 股工具
│   │       ├── agent_states.py
│   │       ├── core_stock_tools.py  # 重构：timelyre 行情
│   │       ├── technical_indicators_tools.py  # 重构：timelyre 技术指标
│   │       ├── fundamental_data_tools.py      # 重构：timelyre 基本面
│   │       ├── news_data_tools.py             # 重构：akshare 新闻
│   │       └── ...
│   ├── dataflows/                   # 重构：仅保留 timelyre + akshare
│   │   ├── __init__.py
│   │   ├── interface.py             # 重构：A 股统一入口
│   │   ├── config.py
│   │   ├── providers/
│   │   │   └── china/
│   │   │       ├── internal.py              # timelyre Provider
│   │   │       ├── internal_queries.py      # timelyre SQL 封装
│   │   │       ├── internal_code_mapper.py  # 股票代码映射
│   │   │       ├── internal_fundamentals_data.py  # 基本面格式化
│   │   │       └── akshare_news.py          # akshare 新闻/舆情
│   │   ├── stock_data_service.py    # A 股数据服务统一层
│   │   └── technical/
│   │       └── stockstats.py        # 技术指标计算
│   ├── graph/                       # 保留：LangGraph 流程不变
│   │   ├── trading_graph.py         # 微调：移除美股 benchmark
│   │   ├── setup.py
│   │   ├── propagation.py
│   │   ├── conditional_logic.py
│   │   ├── reflection.py
│   │   └── signal_processing.py
│   └── llm_clients/                 # 保留：LLM 客户端
│       ├── factory.py
│       ├── openai_client.py
│       ├── anthropic_client.py
│       ├── google_client.py
│       └── ...
├── pyproject.toml                   # 更新依赖
├── .env.example                     # 更新环境变量模板
└── README.md
```

### 4.2 MCP 服务层重构

#### 4.2.1 `tradingagents_mcp/server.py` — FastMCP 工具注册

从参考项目移植，保留核心 Tool，移除非 A 股逻辑：

```python
from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP(
    "TradingAgents-A股",
    instructions="AI金融交易分析Agent — A股多Agent协作分析和单分析师独立调用",
)

# 暴露的 MCP Tools:
# 1. trading_agent      — 完整全流程
# 2. market_analyst     — 独立市场分析
# 3. fundamentals_analyst — 独立基本面分析
# 4. news_analyst       — 独立新闻分析
# 5. social_analyst     — 独立社交情绪分析
# 6. agent_status       — 健康检查
```

#### 4.2.2 `tradingagents_mcp/shared_context.py` — 共享上下文

从参考项目移植，调整配置构建：

- 启动时初始化 LLM + Toolkit 一次，所有 Tool 共享复用
- 缓存 TradingAgentsGraph 实例（按 analysts 组合缓存）
- 与 `create_llms_from_config` 对齐

#### 4.2.3 `tradingagents_mcp/validators.py` — 参数校验

从参考项目移植，精简为 A 股：

- `validate_symbol(symbol)` → 仅识别 6 位数字 A 股代码
- `normalize_date(date_str)` → 支持中文别名（今天/昨天等）
- `nearest_trade_date(date_str)` → 基于 timelyre 交易日历
- `build_config()` → MCP_* 环境变量映射
- `check_health()` → 检查 LLM key + timelyre 连接 + akshare 可用性

#### 4.2.4 `tradingagents_mcp/__main__.py` — 服务入口

从参考项目移植：

```bash
# stdio 模式（默认）
python -m tradingagents_mcp

# HTTP 模式
MCP_TRANSPORT=streamable-http python -m tradingagents_mcp

# 环境自检
python -m tradingagents_mcp check
```

### 4.3 数据源层重构

#### 4.3.1 数据源映射

| 数据类别 | 当前数据源 | 重构后数据源 |
|---------|-----------|------------|
| 行情/K线 | yfinance | **timelyre** (stock_bar_1day) |
| 实时快照 | yfinance | **timelyre** (stock_snapshot) |
| 技术指标 | stockstats + yfinance | **timelyre** K线 + 本地计算 (MA/MACD/RSI/BOLL) |
| 基本面 | simfin/finnhub/yfinance | **timelyre** (capital/finance_indicator/balance/income/cashflow) |
| 估值指标 | yfinance info | **timelyre** (capital 表) |
| 个股新闻 | finnhub/google_news/reddit | **akshare** (东方财富/新浪财经) |
| 宏观新闻 | google_news/reddit/openai | **akshare** (财经新闻) |
| 社交情绪 | reddit/stocktwits | **akshare** (股吧/雪球) |
| 资金流向 | 无 | **timelyre** (stock_money_flow) |
| 股东数据 | 无 | **timelyre** (shareholders_top10/shareholder_num) |
| 分红配股 | 无 | **timelyre** (dividend_allocation) |
| 行业分类 | 无 | **timelyre** (sw_industry) |
| 交易日历 | 无 | **timelyre** (trade_cal) |

#### 4.3.2 `dataflows/providers/china/internal.py` — timelyre Provider

从参考项目移植，核心接口：

```python
class InternalProvider(BaseStockDataProvider):
    # 连接管理
    health_check()                    # JDBC HTTP Proxy 连通性检查

    # 股票基本信息
    get_stock_info(symbol)            # stock_code 表
    get_stock_list()                  # 全量股票列表

    # K 线数据
    get_stock_data(symbol, start, end)  # stock_bar_1day 表

    # 实时行情
    get_stock_quotes(symbol)          # stock_snapshot 表

    # 基本面
    get_fundamentals(symbol)          # capital + finance_indicator + dividend
    get_money_flow(symbol, start, end)  # stock_money_flow 表
    get_market_snapshot()             # 全市场快照（筛选用）
```

#### 4.3.3 `dataflows/providers/china/internal_queries.py` — SQL 封装

从参考项目移植，包含所有 timelyre SQL 查询：

- 环境变量：`JDBC_HTTP_PROXY`, `TM_REAL_CONN`, `TM_DB_NAME`, `TM_DB_USER`, `TM_DB_PASSWORD`, `GUARDIAN_TOKEN`
- 线程安全：全局查询锁（防止 JDBC HTTP Proxy 并发 500）
- 查询函数：`get_daily_kline`, `get_snapshot`, `get_valuation`, `get_finance_indicator`, `get_balance`, `get_income`, `get_cashflow`, `get_money_flow`, `get_dividend`, `get_market_snapshot` 等

#### 4.3.4 `dataflows/providers/china/internal_fundamentals_data.py` — 基本面格式化

从参考项目移植，4 个核心函数：

- `get_fundamentals_overview(symbol, curr_date)` — 公司概览 + 估值 + 关键指标
- `get_balance_sheet_data(symbol, freq, curr_date)` — 资产负债表
- `get_cashflow_data(symbol, freq, curr_date)` — 现金流量表
- `get_income_statement_data(symbol, freq, curr_date)` — 利润表

#### 4.3.5 `dataflows/providers/china/akshare_news.py` — 新闻舆情

新建，使用 akshare 获取 A 股新闻和舆情：

```python
def get_stock_news(symbol, look_back_days=7) -> str
    """个股新闻：东方财富/新浪财经"""

def get_stock_sentiment(symbol) -> str
    """社交舆情：股吧/雪球"""

def get_macro_news() -> str
    """宏观新闻：财经要闻"""
```

### 4.4 @tool 工具重构

当前项目无 Toolkit 类，`@tool` 方法分散在 `agents/utils/` 下各文件中定义，
`agent_utils.py` 仅做集中导入和重导出。重构保持此模式不变，仅替换各文件的数据源调用。

#### 4.4.1 `agents/utils/agent_utils.py` — 工具集中导入 + 辅助函数

不含 Toolkit 类，仅从各子模块导入 `@tool` 函数并重导出，供 graph 和 analyst 使用：

```python
from tradingagents.agents.utils.core_stock_tools import get_stock_data
from tradingagents.agents.utils.technical_indicators_tools import get_indicators
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_money_flow_tool,
)
from tradingagents.agents.utils.news_data_tools import (
    get_news,
    get_global_news
)

def get_language_instruction() -> str: ...
def build_instrument_context(ticker, asset_type="stock") -> str: ...
def create_msg_delete(): ...
```

#### 4.4.2 各工具文件 — 数据源替换

| 文件 | @tool 函数 | 数据源 |
|------|-----------|--------|
| `core_stock_tools.py` | `get_stock_data(symbol, start_date, end_date)` | → `interface.get_stock_data` → timelyre |
| `technical_indicators_tools.py` | `get_indicators(symbol, indicator, curr_date, look_back_days)` | → `interface.get_technical_indicators` → timelyre K线 + 本地计算 |
| `fundamental_data_tools.py` | `get_fundamentals(ticker, curr_date)` | → `interface.get_fundamentals` → timelyre |
| | `get_balance_sheet(ticker, freq, curr_date)` | → `interface.get_balance_sheet` → timelyre |
| | `get_cashflow(ticker, freq, curr_date)` | → `interface.get_cashflow` → timelyre |
| | `get_income_statement(ticker, freq, curr_date)` | → `interface.get_income_statement` → timelyre |
| | `get_money_flow_tool(ticker, start_date, end_date)` | → `interface.get_money_flow` → timelyre（**新增**） |
| `news_data_tools.py` | `get_news(ticker, start_date, end_date)` | → `interface.get_news` → akshare |
| | `get_global_news(curr_date, look_back_days, limit)` | → `interface.get_global_news` → akshare |

移除的工具：`get_insider_transactions`（美股 SEC 内部人交易，A股不适用）

#### 4.4.3 ToolNode 分配（`trading_graph.py`）

```python
def _create_tool_nodes(self) -> Dict[str, ToolNode]:
    return {
        "market": ToolNode([
            get_stock_data,
            get_indicators,
        ]),
        "social": ToolNode([
            get_news,
        ]),
        "news": ToolNode([
            get_news,
            get_global_news,
        ]),
        "fundamentals": ToolNode([
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
            get_money_flow_tool,
        ]),
    }
```

### 4.5 配置重构

#### 4.5.1 `default_config.py`

```python
_TRADINGAGENTS_HOME = os.path.join(os.path.expanduser("~"), ".tradingagents")

DEFAULT_CONFIG = _apply_env_overrides({
    # 目录
    "results_dir": os.path.join(_TRADINGAGENTS_HOME, "logs"),
    "data_cache_dir": os.path.join(_TRADINGAGENTS_HOME, "cache"),
    "memory_log_path": os.path.join(_TRADINGAGENTS_HOME, "memory", "trading_memory.md"),

    # LLM（通过 MCP_* 环境变量覆盖）
    "llm_provider": "openai",
    "deep_think_llm": "gpt-4o",
    "quick_think_llm": "gpt-4o-mini",
    "backend_url": None,

    # 辩论/风险
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    "analyst_concurrency_limit": 1,

    # 输出语言
    "output_language": "Chinese",

    # Benchmark
    "benchmark_ticker": "000300",  # 沪深300
})
```

#### 4.5.2 环境变量

`.env.example`:

```bash
# ===== LLM 配置 =====
MCP_LLM_PROVIDER=openai
MCP_DEEP_THINK_LLM=gpt-4o
MCP_QUICK_THINK_LLM=gpt-4o-mini
MCP_BACKEND_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-xxx

# 支持 DeepSeek / DashScope / Zhipu / Ollama 等
# MCP_LLM_PROVIDER=deepseek
# DEEPSEEK_API_KEY=xxx

# ===== timelyre 内部数据库 =====
JDBC_HTTP_PROXY=172.18.192.74:9998
TM_REAL_CONN=jdbc:hive2://172.18.192.75:10006
TM_DB_NAME=meta_data
TM_DB_USER=admin
TM_DB_PASSWORD=admin
GUARDIAN_TOKEN=xxx

# ===== 运行配置 =====
MCP_PARALLEL_ANALYSTS=true
MCP_MAX_DEBATE_ROUNDS=1
MCP_MAX_RISK_DISCUSS_ROUNDS=1
TRADINGAGENTS_LOG_LEVEL=INFO
```

### 4.6 日志与缓存

#### 4.6.1 日志配置

统一存储于 `~/.tradingagents/logs/`，每天滚动，保留 7 天：

```python
# tradingagents_mcp/__main__.py

def _setup_logging():
    log_dir = os.path.join(os.path.expanduser("~"), ".tradingagents", "logs")
    config = {
        "handlers": {
            "file": {
                "enabled": True,
                "level": "DEBUG",
                "backup_count": 7,        # 保留 7 天
                "directory": log_dir,
            },
            "error": {
                "enabled": True,
                "level": "WARNING",
                "backup_count": 7,
                "directory": log_dir,
                "filename": "error.log",
            },
        },
    }
```

#### 4.6.2 缓存目录

```
~/.tradingagents/
├── logs/                # 日志（滚动 7 天）
│   ├── tradingagents.log
│   ├── tradingagents.log.1
│   └── error.log
├── cache/               # 数据缓存
├── memory/              # 交易记忆
│   └── trading_memory.md
└── results/             # 分析结果
```

### 4.7 依赖更新

`pyproject.toml` 新增/移除依赖：

```toml
dependencies = [
    # MCP
    "mcp[cli]>=1.0.0",
    # LangChain
    "langchain-core>=0.3.81",
    "langchain-openai>=0.3.23",
    "langchain-anthropic>=0.3.15",
    "langchain-google-genai>=4.0.0",
    "langchain-experimental>=0.3.4",
    "langgraph>=0.4.8",
    # 数据源
    "timelyre-api==1.4.0",
    "akshare>=1.17.86",
    # 通用
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    "stockstats>=0.6.5",
    "pytz>=2025.2",
    "requests>=2.32.4",
]

# 移除的依赖：
# - yfinance（不再需要）
# - finnhub-python（不再需要）
# - alpha_vantage（不再需要）
# - baostock（不再需要）
# - tushare（不再需要）
# - redis（不再需要）
# - backtrader（不再需要）
```

### 4.8 pyproject.toml 入口更新

```toml
[project.scripts]
tradingagents-mcp = "tradingagents_mcp.__main__:main"
```

---

## 5. 实施计划

### 阶段一：MCP 服务层搭建（1-2 天）

| 任务 | 说明 |
|------|------|
| 创建 `tradingagents_mcp/` 包 | 从参考项目移植 server.py、shared_context.py、validators.py、trade_calendar.py、__main__.py、prompts.py |
| 精简 validators | 移除美股/港股识别逻辑，仅保留 A 股 6 位代码校验 |
| 精简 agent_status | 移除非 A 股数据源检查，添加 timelyre + akshare 检查 |
| 配置日志 | 统一到 `~/.tradingagents/logs/`，7 天滚动 |

### 阶段二：数据源替换（2-3 天）

| 任务 | 说明 |
|------|------|
| 移植 `providers/china/internal.py` | timelyre Provider（从参考项目移植） |
| 移植 `providers/china/internal_queries.py` | SQL 封装（从参考项目移植） |
| 移植 `providers/china/internal_code_mapper.py` | 代码映射（从参考项目移植） |
| 移植 `providers/china/internal_fundamentals_data.py` | 基本面格式化（从参考项目移植） |
| 新建 `providers/china/akshare_news.py` | akshare 新闻/舆情 |
| 重构 `dataflows/interface.py` | 统一入口仅走 timelyre + akshare |
| 移除旧数据源 | 删除 yfinance/alpha_vantage/finnhub/reddit/simfin 等相关文件 |

### 阶段三：@tool 工具重构（1-2 天）

| 任务 | 说明 |
|------|------|
| 更新 `agents/utils/agent_utils.py` 导入 | 替换导入为 A 股工具，移除 `get_insider_transactions`，简化 `build_instrument_context` |
| 重构 `agents/utils/core_stock_tools.py` | `get_stock_data` → timelyre |
| 重构 `agents/utils/technical_indicators_tools.py` | `get_indicators` → timelyre K 线 + 本地计算（`dataflows/technical/stockstats.py`） |
| 重构 `agents/utils/fundamental_data_tools.py` | 新增 `get_money_flow_tool`，全部走 timelyre |
| 重构 `agents/utils/news_data_tools.py` | `get_news`/`get_global_news` → akshare |
| 重构 `agents/analysts/sentiment_analyst.py` | Reddit/StockTwits → akshare 股吧舆情 |
| 更新 `trading_graph.py` ToolNode | 使用新的工具函数 + 移除 yfinance 依赖 |

### 阶段四：配置与清理（1 天）

| 任务 | 说明 |
|------|------|
| 重构 `default_config.py` | A 股默认配置 + MCP_* 环境变量 |
| 更新 `.env.example` | timelyre + LLM 环境变量模板 |
| 更新 `pyproject.toml` | 依赖、入口、移除旧包 |
| 清理旧代码 | 移除美股/港股相关代码、旧 dataflows 文件 |
| 更新 `README.md` | A 股使用说明 |

### 阶段五：测试验证（1-2 天）

| 任务 | 说明 |
|------|------|
| 环境自检 | `python -m tradingagents_mcp check` |
| 单分析师测试 | market_analyst / fundamentals_analyst / news_analyst / social_analyst |
| 全流程测试 | trading_agent 完整流程 |
| 健康检查测试 | agent_status |
| 日志验证 | 确认日志写入 `~/.tradingagents/logs/` 并滚动 |

---

## 6. 风险与注意事项

| 风险 | 缓解措施 |
|------|---------|
| timelyre 连接不稳定 | 暂不做降级，直接报错提示用户检查 JDBC_HTTP_PROXY 配置 |
| akshare 接口变更 | 封装为独立模块，变更时仅需修改 akshare_news.py |
| timelyre 数据延迟 | 在 health_check 中检测最新数据日期，提醒用户 |
| LLM Provider 兼容性 | 保留多 Provider 支持（openai/deepseek/dashscope/zhipu/ollama 等） |
| 当前项目分析流程被破坏 | 仅替换数据源和 MCP 层，不修改 agents/graph 核心逻辑 |

---

## 7. 验收标准

1. `python -m tradingagents_mcp check` 通过，显示 timelyre 连接正常 + LLM key 配置正确 + akshare 可用
2. `market_analyst(symbol="000001", trade_date="2025-05-30")` 返回技术分析报告
3. `fundamentals_analyst(symbol="000001", trade_date="2025-05-30")` 返回基本面分析报告
4. `news_analyst(symbol="000001", trade_date="2025-05-30")` 返回新闻分析报告
5. `social_analyst(symbol="000001", trade_date="2025-05-30")` 返回社交情绪报告
6. `trading_agent(symbol="000001", trade_date="2025-05-30")` 完成全流程分析并返回交易决策
7. `agent_status()` 返回健康状态和配置信息
8. 日志文件存储于 `~/.tradingagents/logs/`，按天滚动，保留 7 天
9. 无 yfinance/finnhub/alpha_vantage/baostock/tushare 相关代码残留
