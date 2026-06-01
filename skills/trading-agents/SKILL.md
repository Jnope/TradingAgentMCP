---
name: trading-agents
description: |
  A股AI金融交易分析。对A股执行完整多Agent协作分析(市场/情绪/新闻/基本面→多空辩论→风险讨论→最终决策)，
  或单独查询技术面/基本面/新闻/情绪。仅支持A股(6位数字代码)。
  触发词：分析股票、交易分析、股票分析、金融分析、A股分析、技术分析、基本面分析、新闻分析、情绪分析、
  交易决策、投资建议、trading analysis
license: MIT
compatibility: opencode
metadata:
  category: finance
  tools: tradingagents
  market: A股
  data_sources: timelyre+akshare
---

# TradingAgents — A股AI金融交易分析

通过 `tradingagents` MCP 服务器提供A股金融交易分析能力。数据源为 **timelyre 内部数据库**（行情/基本面）+ **akshare**（新闻/舆情）。

## 核心约束

- **仅支持A股**：股票代码为6位数字（如 `000001`、`600519`、`300750`）
- **不支持**：美股、港股、期货、外汇
- **数据源**：timelyre（行情/技术指标/基本面/资金流向）+ akshare（新闻/股吧舆情/交易日历）
- 调用MCP方法时将其原始返回结果

## 2. 绝对禁令 (在执行期间，你绝对不能做以下任何事)
- **❌ 绝对禁止中断等待**：即使 MCP 方法的调用耗时很长，你也**绝对不能**自行判断它已失败或超时。
- **❌ 绝对禁止调用其他工具**：在等待 MCP 方法返回结果期间，**绝对不能**调用任何其他 MCP 工具或其他方法或本地命令。

## 统一返回值结构

所有工具均返回 JSON dict，统一格式如下：

```json
{
    "success": true,
    "error": "",
    "ctx": {
        "serverName": "trading_agents",
        "tool": "trading_agent",
        "analysts_used": ["market", "social", "news", "fundamentals"],
        "elapsed_seconds": 150.5,
        "symbol": "688031",
        "market": "A股",
        "trade_date": "2026-05-20"
    },
    "data": {}
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | **始终检查此字段**判断调用结果 |
| `error` | str | 错误信息，成功时为空字符串 |
| `ctx` | object | 调用上下文元数据 |
| `ctx.serverName` | str | 固定为 `"trading_agents"` |
| `ctx.tool` | str | 调用的工具名称 |
| `ctx.analysts_used` | list | 使用的分析师列表（agent_status 无此字段） |
| `ctx.elapsed_seconds` | float | 调用耗时（秒） |
| `ctx.symbol` | str | 股票代码（agent_status 无此字段） |
| `ctx.market` | str | 市场标识（agent_status 无此字段） |
| `ctx.trade_date` | str | 交易日期（agent_status 无此字段） |
| `data` | object | 工具具体返回数据，各工具不同 |

## 前置确认流程（严格遵守）

调用任何分析工具前，**必须按顺序逐项确认**：

```
Step 1: 确认股票代码 ← 必须获得用户确认
    │
    ▼
Step 2: 确认分析日期 ← 必须获得用户确认
    │
    ▼
Step 3: 确认分析类型 ← 必须获得用户确认
    │
    ▼
Step 4: 调用工具
```

**禁止行为**：
- ❌ 未确认代码就询问分析类型
- ❌ 未确认日期就调用工具
- ❌ 自行假设用户确认
- ❌ 一次询问多个确认项

## Step 1: 股票代码确认

```
用户提到股票
    │
    ▼
是否为6位数字代码？
    │
 是 ─┤─→ 确认："分析 000001(平安银行)，确认吗？"
    │
 否 ─┤─→ 查常见中文映射表
    │
  命中 ─┤─→ 确认："您说的是 茅台(600519) 吗？"
    │
  未命中 ─┤─→ 要求用户手动输入6位A股代码
```

**关键规则**：绝不猜测代码，即使映射命中也必须确认。

### 股票代码格式

**A股**: 6位数字 — `000001`(平安银行)、`600519`(茅台)、`300750`(宁德时代)、`002594`(比亚迪)

### 常见中文股票名映射

| 名称 | 代码 | 名称 | 代码 |
|------|------|------|------|
| 茅台/贵州茅台 | 600519 | 平安银行 | 000001 |
| 招商银行 | 600036 | 五粮液 | 000858 |
| 宁德时代 | 300750 | 比亚迪 | 002594 |
| 工商银行 | 601398 | 中国平安 | 601318 |
| 美的集团 | 000333 | 格力电器 | 000651 |
| 中信证券 | 600030 | 海康威视 | 002415 |
| 隆基绿能 | 601012 | 中国中免 | 601888 |
| 药明康德 | 603259 | 紫金矿业 | 601899 |
| 长江电力 | 600900 | 中国移动 | 600941 |
| 中国石油 | 601857 | 中国神华 | 601088 |

**常见指数**: 000300(沪深300)、000016(上证50)、000905(中证500)、399006(创业板指)、000001(上证指数)、399001(深证成指)、000688(科创50)

## Step 2: 日期确认

1. 用户已指定日期 → 确认
2. 用户说"今天"/"昨天" → 解析后确认（"昨天"自动跳周末）
3. 用户未指定 → **必须询问**，默认今天

## Step 3: 分析类型确认

用户未明确指定时，询问：

1. **全面分析**（trading_agent）— 技术+基本面+新闻+情绪+辩论+决策，3-10分钟
2. **仅技术面**（market_analyst）— K线/均线/MACD/RSI，~30秒
3. **仅基本面**（fundamentals_analyst）— PE/PB/ROE/估值，~30秒
4. **仅新闻**（news_analyst）— 重大事件/政策，~30秒
5. **仅情绪**（social_analyst）— 股吧舆情/散户观点，~30秒

**意图映射**：
- "全面分析"/"投资建议"/"要不要买" → `trading_agent`
- "技术面"/"走势"/"K线" → `market_analyst`
- "估值"/"基本面"/"PE" → `fundamentals_analyst`
- "新闻"/"利好利空" → `news_analyst`
- "大家怎么看"/"情绪" → `social_analyst`
- **模糊表述（如"分析一下"）必须询问确认**

## Step 4: 环境检查（首次使用时执行一次）

- 调用 `agent_status()` 确认环境就绪
- `health.llm_api_key` 含 "missing" → 提示用户检查 `.opencode.json` 中 environment 配置
- `health.timelyre` 不为 "ok" → 提示用户检查 JDBC_HTTP_PROXY 等配置
- `health.akshare` 不为 "ok" → 提示用户 `pip install akshare`

---

## 工具详细说明

### 工具 1: `trading_agent` — 完整全流程分析

**耗时**: 3-10 分钟

**参数**:
- `symbol` (必选): 6位A股代码
- `trade_date` (必选): 交易日期 YYYY-MM-DD
- `analysts` (可选): 分析师组合，默认 `["market","social","news","fundamentals"]`
- `max_debate_rounds` (可选): 多空辩论轮次，默认 1
- `max_risk_discuss_rounds` (可选): 风险辩论轮次，默认 1
- `parallel_analysts` (可选): 分析师是否并行，默认读取 MCP_PARALLEL_ANALYSTS

**返回值** (`data` 字段内容):
| 字段 | 说明 |
|------|------|
| `market_report` | 市场技术分析报告 |
| `fundamentals_report` | 基本面分析报告 |
| `sentiment_report` | 社交情绪报告 |
| `news_report` | 新闻分析报告 |
| `investment_debate` | 多空辩论结果（bull_history/bear_history/judge_decision） |
| `trader_investment_plan` | 交易员投资方案（操作/理由/入场价/止损/仓位） |
| `risk_debate` | 风险讨论结果（aggressive_history/conservative_history/neutral_history/judge_decision） |
| `investment_plan` | 研究经理投资计划（建议/理由/战略行动） |
| `final_trade_decision` | 投资组合经理最终决策（含评级：买入/增持/持有/减持/卖出 + 执行摘要 + 投资逻辑 + 目标价 + 时间周期） |

**调用前必须告知**: "全流程分析需要 3-10 分钟，请耐心等待"

**示例**:
```
trading_agent(symbol="600519", trade_date="2025-05-30")
```

### 工具 2: `market_analyst` — 技术面分析

**耗时**: ~30 秒

**参数**:
- `symbol` (必选): 6位A股代码
- `trade_date` (必选): 交易日期 YYYY-MM-DD

**返回值** (`data` 字段内容):
| 字段 | 说明 |
|------|------|
| `market_report` | 技术分析报告（MA/MACD/RSI/BOLL/趋势/成交量） |

**示例**:
```
market_analyst(symbol="000001", trade_date="2025-05-30")
```

### 工具 3: `fundamentals_analyst` — 基本面分析

**耗时**: ~30 秒

**参数**:
- `symbol` (必选): 6位A股代码
- `trade_date` (必选): 交易日期 YYYY-MM-DD

**返回值** (`data` 字段内容):
| 字段 | 说明 |
|------|------|
| `fundamentals_report` | 基本面报告（估值/盈利/财务健康/行业对比） |

**示例**:
```
fundamentals_analyst(symbol="000001", trade_date="2025-05-30")
```

### 工具 4: `news_analyst` — 新闻分析

**耗时**: ~30 秒

**参数**:
- `symbol` (必选): 6位A股代码
- `trade_date` (必选): 交易日期 YYYY-MM-DD
- `look_back_days` (可选): 回看天数，默认 7

**返回值** (`data` 字段内容):
| 字段 | 说明 |
|------|------|
| `news_report` | 新闻分析报告（重大事件/政策影响/行业动态） |
| `look_back_days` | 实际回看天数 |

**示例**:
```
news_analyst(symbol="000001", trade_date="2025-05-30", look_back_days=14)
```

### 工具 5: `social_analyst` — 社交情绪分析

**耗时**: ~30 秒

**参数**:
- `symbol` (必选): 6位A股代码
- `trade_date` (必选): 交易日期 YYYY-MM-DD

**返回值** (`data` 字段内容):
| 字段 | 说明 |
|------|------|
| `sentiment_report` | 情绪分析报告（股吧舆情/投资者情绪/多空倾向） |

**注意**: A股社交数据源有限（东方财富股吧），可能返回数据不足

**示例**:
```
social_analyst(symbol="000001", trade_date="2025-05-30")
```

### 工具 6: `agent_status` — 健康检查与配置查询

**参数**: 无

**返回值** (`data` 字段内容):
| 字段 | 说明 |
|------|------|
| `version` | MCP Server 版本 |
| `health` | 健康检查: mcp_server/llm_api_key/akshare/timelyre |
| `supported_markets` | ["A股"] |
| `available_tools` | 所有可用工具及说明 |
| `data_sources` | 数据源信息 |

**何时使用**:
- 分析前环境自检（首次使用时执行一次）
- 排查连接问题
- 用户问"你能做什么"/"支持什么"

---

## 意图路由速查表

| 用户话术 | MCP Tool | 关键参数 |
|---------|----------|---------|
| 全面分析/投资建议/要不要买 | `trading_agent` | symbol, trade_date |
| 技术面/走势/K线/均线/MACD | `market_analyst` | symbol, trade_date |
| 基本面/估值/PE/贵不贵 | `fundamentals_analyst` | symbol, trade_date |
| 新闻/利好利空/消息/政策 | `news_analyst` | symbol, trade_date |
| 情绪/大家怎么看/散户/股吧 | `social_analyst` | symbol, trade_date |
| 你能做什么/配置/支持什么 | `agent_status` | — |
| 环境检查/健康检查 | `agent_status` | — |

## 耗时预期管理

调用耗时较长的工具前，**必须**告知用户：

| 工具 | 预计耗时 | 用户提示 |
|------|---------|---------|
| `trading_agent` | 3-10 分钟 | "全流程分析需要 3-10 分钟，请耐心等待" |
| 单分析师 | ~30 秒 | "正在分析，大约需要 30 秒" |
| `agent_status` | <1 秒 | 无需提示 |

## 错误恢复指引

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| MCP 连接失败 | Server 未启动 | 检查 `.opencode.json` 中 command/args |
| API Key 错误 | 环境变量未配 | 在 `.opencode.json` environment 中添加 |
| timelyre 不可用 | JDBC_HTTP_PROXY 配置错误 | 检查 timelyre 相关环境变量 |
| A股数据获取失败 | akshare 未安装或网络问题 | `pip install akshare`，检查网络 |
| 股票代码无效 | 非6位数字 | 确认6位A股代码格式 |
| 分析超时 | 全流程+多辩论轮次 | 先用 `market_analyst` 快速验证 |
| 社交分析无数据 | A股社交源有限 | 改用 `news_analyst` 替代 |
| health.llm_api_key 含 missing | API Key 未设置 | 检查对应供应商的 Key 配置 |

## LLM 供应商配置

| 供应商 | MCP_LLM_PROVIDER | API Key 环境变量 | Backend URL |
|--------|-------------------|-----------------|-------------|
| OpenAI | `openai` | `OPENAI_API_KEY` | https://api.openai.com/v1 |
| 阿里通义 | `dashscope` | `DASHSCOPE_API_KEY` | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| DeepSeek | `deepseek` | `DEEPSEEK_API_KEY` | https://api.deepseek.com/v1 |
| Google | `google` | `GOOGLE_API_KEY` | — |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | — |
| 智谱 | `zhipu` | `ZHIPU_API_KEY` | — |
| Ollama | `ollama` | 无需 | http://localhost:11434/v1 |

## MCP 配置参考

在 `.opencode.json` 中配置：

```json
{
  "mcp": {
    "tradingagents": {
      "type": "local",
      "command": ["tradingagents-mcp"],
      "timeout": 0,
      "environment": {
        "MCP_LLM_PROVIDER": "dashscope",
        "MCP_DEEP_THINK_LLM": "qwen-max",
        "MCP_QUICK_THINK_LLM": "qwen-turbo",
        "MCP_BACKEND_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "DASHSCOPE_API_KEY": "sk-xxx",
        "JDBC_HTTP_PROXY": "172.18.192.74:9998",
        "TM_REAL_CONN": "jdbc:hive2://172.18.192.75:10006",
        "TM_DB_NAME": "meta_data",
        "TM_DB_USER": "admin",
        "TM_DB_PASSWORD": "admin",
        "GUARDIAN_TOKEN": "xxx"
      }
    }
  }
}
```

## MCP Prompts（预置对话模板）

MCP Server 注册了 5 个 Prompt 模板：

| Prompt 标题 | 参数 | 用途 |
|------------|------|------|
| 股票分析 | symbol, trade_date | 触发 trading_agent 全流程 |
| 技术面分析 | symbol, trade_date | 触发 market_analyst |
| 基本面分析 | symbol, trade_date | 触发 fundamentals_analyst |
| 新闻分析 | symbol, trade_date | 触发 news_analyst |
| 情绪分析 | symbol, trade_date | 触发 social_analyst |

## 数据源详情

| 数据类别 | 数据源 | 表/接口 |
|---------|--------|---------|
| 日K线 | timelyre | stock_bar_1day |
| 技术指标 | timelyre K线 + 本地计算 | MA/MACD/RSI/BOLL/ATR/MFI |
| 基本面概览 | timelyre | capital + finance_indicator + dividend |
| 资产负债表 | timelyre | balance |
| 利润表 | timelyre | income |
| 现金流量表 | timelyre | cashflow |
| 资金流向 | timelyre | stock_money_flow |
| 个股新闻 | akshare | 东方财富/新浪财经 |
| 社交情绪 | akshare | 东方财富股吧 |
| 宏观新闻 | akshare | 财经要闻 |
| 交易日历 | timelyre / akshare | trade_cal |
