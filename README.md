# TradingAgents MCP — A股AI金融交易分析

基于多Agent协作的A股交易分析框架，通过MCP协议提供服务。

## 框架概述

TradingAgents 采用多Agent协作架构，模拟真实交易团队的工作流程：

- **分析师团队**：市场分析师、基本面分析师、新闻分析师、社交情绪分析师
- **研究员团队**：多头/空头研究员，通过结构化辩论平衡收益与风险
- **交易员**：综合分析师生成的报告，做出交易决策
- **风控团队**：评估投资风险，调整交易策略

## 数据源

| 数据类别 | 数据源 |
|---------|--------|
| 行情/K线 | timelyre 内部数据库 (stock_bar_1day) |
| 技术指标 | timelyre K线 + 本地计算 (MA/MACD/RSI/BOLL) |
| 基本面 | timelyre (capital/finance_indicator/balance/income/cashflow) |
| 个股新闻 | akshare (东方财富/新浪财经) |
| 社交情绪 | akshare (东方财富股吧) |
| 交易日历 | timelyre / akshare |

## 安装

```bash
# 克隆项目
git clone <repo-url>
cd TradingAgentsMCP

# 创建虚拟环境
conda create -n tradingagents python=3.12
conda activate tradingagents
pip install .

# 或使用 uv
uv sync
```

## 配置

复制环境变量模板并填写：

```bash
cp .env.example .env
```

关键配置项：

```bash
# LLM 配置
MCP_LLM_PROVIDER=openai          # openai/deepseek/dashscope/zhipu/ollama 等
MCP_DEEP_THINK_LLM=gpt-4o       # 深度思考模型
MCP_QUICK_THINK_LLM=gpt-4o-mini # 快速推理模型
MCP_BACKEND_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-xxx

# timelyre 内部数据库
JDBC_HTTP_PROXY=172.18.192.74:9998
TM_REAL_CONN=jdbc:hive2://172.18.192.75:10006
TM_DB_NAME=meta_data
TM_DB_USER=admin
TM_DB_PASSWORD=admin
GUARDIAN_TOKEN=xxx

# 运行配置
MCP_PARALLEL_ANALYSTS=true
MCP_MAX_DEBATE_ROUNDS=1
MCP_MAX_RISK_DISCUSS_ROUNDS=1
TRADINGAGENTS_LOG_LEVEL=INFO
```

## 启动 MCP 服务

```bash
# 打包
uv build --wheel

# 全局安装
pipx install ./dist/tradingagents-1.0.0-py3-none-any.whl   --force   --pip-args="--find-links ./wheelhouse"

# stdio 模式（默认，适用于 Claude Desktop 等客户端）
tradingagents-mcp
# 或
uv run
# 或
python -m tradingagents_mcp

# HTTP 模式
MCP_TRANSPORT=streamable-http tradingagents-mcp

# 环境自检
tradingagents-mcp check
# 或
python -m tradingagents_mcp check
```

## MCP 工具列表

| 工具 | 功能 | 耗时     |
|------|------|--------|
| `trading_agent` | 完整全流程分析（分析师→辩论→风险→决策） | 3-30分钟 |
| `market_analyst` | 独立市场/技术分析 | 1~10分钟 |
| `fundamentals_analyst` | 独立基本面分析 | 1~10分钟   |
| `news_analyst` | 独立新闻分析 | 1~10分钟  |
| `social_analyst` | 独立社交情绪分析 | 1~10分钟  |
| `agent_status` | 健康检查与配置查询 | 即时     |

## Python 用法

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("000001", "2025-05-30")
print(decision)
```

## 日志与缓存

所有数据统一存储于 `~/.tradingagents/`：

```
~/.tradingagents/
├── logs/                # 日志（按天滚动，保留7天）
│   ├── tradingagents.log
│   └── error.log
├── cache/               # 数据缓存
├── memory/              # 交易记忆
│   └── trading_memory.md
└── results/             # 分析结果
```

## 支持的 LLM Provider

OpenAI、DeepSeek、DashScope(通义千问)、Zhipu(智谱)、Anthropic、Google、xAI、MiniMax、OpenRouter、SiliconFlow、Ollama（本地模型）、Azure OpenAI。

## 免责声明

本项目仅供研究用途，不构成任何金融、投资或交易建议。
