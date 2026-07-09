---
name: trading-agents
description: |
  A股AI金融交易分析，用于对A股执行完整多Agent协作分析(市场/情绪/新闻/基本面→多空辩论→风险讨论→最终决策)，或单独查询技术面即市场/基本面/新闻/情绪；
  仅支持A股(6位数字代码)；
  远程地址为 http://172.18.192.76:19876/mcp。
  触发词：分析股票、交易分析、股票分析、金融分析、A股分析、技术面分析、市场分析、基本面分析、新闻分析、情绪分析、交易决策、投资建议。
license: MIT
metadata:
  category: finance
---

# trading-agents 使用

## 远程服务信息

- **地址**: `http://172.18.192.76:19876/mcp`
- **传输协议**: Streamable HTTP Transport (SSE over HTTP)
- **服务内容**: A股金融交易分析（TradingAgents）

## 可用工具一览

| 工具 | 说明 | 耗时 |
|------|------|------|
| `agent_status` | 环境健康检查 | <10秒 |
| `market_analyst` | 市场技术分析 | 1-10分钟 |
| `fundamentals_analyst` | 基本面分析 | 1-10分钟 |
| `news_analyst` | 新闻分析 | 1-10分钟 |
| `social_analyst` | 社交媒体情绪分析 | 1-10分钟 |
| `trading_agent` | 完整全流程分析 | 3-30分钟 |

## 调用流程（3步）

### 步骤1：初始化（获取 Session ID）

```bash
TMP=$(mktemp)
curl -s -D "$TMP" -X POST http://172.18.192.76:19876/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"ai-agent","version":"1.0"}}}'

SID=$(grep -i 'mcp-session-id' "$TMP" | tr -d '\r' | awk '{print $2}')
echo "SESSION_ID=$SID"
```

### 步骤2：发送 initialized 通知

```bash
curl -s -X POST http://172.18.192.76:19876/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' > /dev/null
```

### 步骤3：调用工具

```bash
curl -s -X POST http://172.18.192.76:19876/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "agent_status",
      "arguments": {}
    }
  }'
```

## 查看所有可用工具

```bash
curl -s -X POST http://172.18.192.76:19876/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

## 工具调用参数

### agent_status
```json
{"name": "agent_status", "arguments": {}}
```

### market_analyst
```json
{"name": "market_analyst", "arguments": {"symbol": "000001", "trade_date": "2026-07-08"}}
```

### fundamentals_analyst
```json
{"name": "fundamentals_analyst", "arguments": {"symbol": "000001", "trade_date": "2026-07-08"}}
```

### news_analyst
```json
{"name": "news_analyst", "arguments": {"symbol": "000001", "trade_date": "2026-07-08", "look_back_days": 7}}
```

### social_analyst
```json
{"name": "social_analyst", "arguments": {"symbol": "000001", "trade_date": "2026-07-08"}}
```

### trading_agent（完整全流程）
```json
{
  "name": "trading_agent",
  "arguments": {
    "symbol": "000001",
    "trade_date": "2026-07-08",
    "analysts": ["market", "social", "news", "fundamentals"],
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "parallel_analysts": true,
    "detail": false
  }
}
```

## 响应解析

响应为 SSE 格式，`data` 行内容示例：
```
data: {"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"{...}"}],"isError":false}}
```

最终结果在 `result.content[0].text` 中，是 JSON 字符串，需额外解析一次。

### 外层 SSE 响应结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `jsonrpc` | string | 固定 `"2.0"`，JSON-RPC 协议版本 |
| `id` | int | 请求 ID，与调用时的 `id` 对应 |
| `result.content` | array | 内容数组，`content[0].text` 为工具返回的 JSON 字符串 |
| `result.content[0].type` | string | 固定 `"text"` |
| `result.content[0].text` | string | 工具返回的 JSON 字符串，需二次 `JSON.parse()` |
| `result.isError` | bool | `false` 表示工具执行成功；`true` 表示工具内部报错 |
| `error` | object | 仅当 JSON-RPC 层面出错时存在（如方法不存在、参数校验失败） |

### 内层工具返回结构（content[0].text 解析后）

所有工具返回统一 JSON 结构：

```json
{
  "success": true,
  "error": "",
  "ctx": {
    "server_name": "TradingAgents",
    "tool": "market_analyst",
    "elapsed_seconds": 32.5,
    "symbol": "000001",
    "market": "A股",
    "company_name": "平安银行",
    "trade_date": "2026-07-08",
    "analysts_used": ["market"]
  },
  "data": {}
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 工具调用是否成功 |
| `error` | string | 失败时的错误信息，成功时为空字符串 |
| `ctx.server_name` | string | 固定 `"TradingAgents"` |
| `ctx.tool` | string | 调用的工具名称 |
| `ctx.elapsed_seconds` | float | 工具执行耗时（秒） |
| `ctx.symbol` | string | 股票代码 |
| `ctx.market` | string | 市场，固定 `"A股"` |
| `ctx.company_name` | string | 公司名称（如"平安银行"） |
| `ctx.trade_date` | string | 实际分析的交易日期（YYYY-MM-DD） |
| `ctx.analysts_used` | array | 使用的分析师列表 |
| `data` | object | 工具返回的具体数据，因工具而异（见下文） |

### 各工具 data 字段说明

#### agent_status 的 data

```json
{
  "version": "1.0.0",
  "health": {
    "mcp_server": "ok",
    "llm_api_key": "ok",
    "akshare": "ok",
    "timelyre": "ok"
  },
  "supported_markets": ["A股"],
  "available_tools": {
    "trading_agent": "完整全流程分析（分析师→辩论→风险→决策，3-10分钟）",
    "market_analyst": "独立市场/技术分析（~30秒）",
    "fundamentals_analyst": "独立基本面分析（~30秒）",
    "news_analyst": "独立新闻分析（~30秒）",
    "social_analyst": "独立社交媒体情绪分析（~30秒）"
  },
  "data_sources": {
    "A股行情/基本面": "timelyre 内部数据库",
    "新闻/舆情": "akshare"
  },
  "llm_provider": "openai",
  "deep_think_llm": "xclaw/glm-5.1",
  "quick_think_llm": "openai/deepseek-v4-flash",
  "parallel_analysts": true
}
```

| 字段 | 说明 |
|------|------|
| `health.mcp_server` | MCP 服务状态，`"ok"` 为正常 |
| `health.llm_api_key` | LLM API Key 状态，含 `"missing"` 表示未配置 |
| `health.akshare` | akshare 数据源状态 |
| `health.timelyre` | timelyre 内部数据库状态，`"ok"` 为正常 |
| `available_tools` | 可用工具列表及说明 |
| `llm_provider` | LLM 提供商 |
| `deep_think_llm` | 深度思考模型 |
| `quick_think_llm` | 快速思考模型 |
| `parallel_analysts` | 分析师是否并行执行 |

#### market_analyst 的 data

```json
{
  "market_report": "技术分析报告文本，包含移动平均线、MACD、RSI、布林带、价格趋势、成交量分析..."
}
```

| 字段 | 说明 |
|------|------|
| `market_report` | 市场技术分析报告，涵盖均线系统、MACD、RSI、布林带、量价关系等技术指标 |

#### fundamentals_analyst 的 data

```json
{
  "fundamentals_report": "基本面分析报告文本，包含PE/PB/ROE等估值和盈利能力分析..."
}
```

| 字段 | 说明 |
|------|------|
| `fundamentals_report` | 基本面分析报告，涵盖估值指标（PE/PB）、盈利能力（ROE）、财务健康、行业对比 |

#### news_analyst 的 data

```json
{
  "news_report": "新闻分析报告文本，包含重大新闻事件、政策影响、行业动态...",
  "look_back_days": 7
}
```

| 字段 | 说明 |
|------|------|
| `news_report` | 新闻分析报告，涵盖重大新闻事件、政策影响、行业动态、潜在风险 |
| `look_back_days` | 回看天数 |

#### social_analyst 的 data

```json
{
  "sentiment_report": "社交媒体情绪分析报告文本，包含投资者情绪、讨论热度、多空倾向..."
}
```

| 字段 | 说明 |
|------|------|
| `sentiment_report` | 社交媒体情绪报告，涵盖投资者情绪、讨论热度、关键观点、多空倾向 |

#### trading_agent 的 data

```json
{
  "company_name": "平安银行",
  "market_report": "市场技术分析报告（摘要）",
  "fundamentals_report": "基本面分析报告（摘要）",
  "sentiment_report": "社交媒体情绪报告（摘要）",
  "news_report": "新闻分析报告（摘要）",
  "investment_debate": {
    "bull_history": "看涨分析师辩论发言",
    "bear_history": "看跌分析师辩论发言",
    "judge_decision": "研究主管裁决发言"
  },
  "trader_investment_plan": "交易员投资计划",
  "risk_debate": {
    "aggressive_history": "激进风险分析师发言",
    "conservative_history": "保守风险分析师发言",
    "neutral_history": "中性风险分析师发言",
    "judge_decision": "风险讨论裁决"
  },
  "investment_plan": "最终投资计划",
  "final_trade_decision": "最终交易决策"
}
```

| 字段 | 说明 |
|------|------|
| `company_name` | 公司名称 |
| `market_report` | 市场技术分析报告（`detail=false` 时为摘要，`detail=true` 时为完整报告） |
| `fundamentals_report` | 基本面分析报告 |
| `sentiment_report` | 社交媒体情绪报告 |
| `news_report` | 新闻分析报告 |
| `investment_debate.bull_history` | 看涨分析师的多空辩论发言 |
| `investment_debate.bear_history` | 看跌分析师的多空辩论发言 |
| `investment_debate.judge_decision` | 研究主管在多空辩论后的裁决发言 |
| `trader_investment_plan` | 交易员基于辩论结果制定的投资计划 |
| `risk_debate.aggressive_history` | 激进风险分析师的发言 |
| `risk_debate.conservative_history` | 保守风险分析师的发言 |
| `risk_debate.neutral_history` | 中性风险分析师的发言 |
| `risk_debate.judge_decision` | 风险讨论后的最终裁决 |
| `investment_plan` | 综合所有分析后的投资计划 |
| `final_trade_decision` | **最终交易决策**，是整个分析流程的核心输出 |

> **提示**: `trading_agent` 的 `detail` 参数设为 `true` 时，各报告字段返回完整内容；默认 `false` 返回 LLM 生成的摘要。

## 通用调用脚本

`call_mcp.sh` — 封装 HTTP MCP 调用的3步流程（initialize → initialized → tools/call），自动处理 SSE 响应解析。

### call_mcp.sh 使用方式

```bash
# 语法
./call_mcp.sh <tool_name> '<json_arguments>'
```

#### 单分析工具（直接输出可读报告文本）

```bash
# 健康检查
./call_mcp.sh agent_status '{}'

# 市场技术分析
./call_mcp.sh market_analyst '{"symbol":"688031","trade_date":"2026-07-08"}'

# 基本面分析
./call_mcp.sh fundamentals_analyst '{"symbol":"688031","trade_date":"2026-07-08"}'

# 新闻分析
./call_mcp.sh news_analyst '{"symbol":"688031","trade_date":"2026-07-08","look_back_days":7}'

# 情绪分析
./call_mcp.sh social_analyst '{"symbol":"688031","trade_date":"2026-07-08"}'
```

> 单分析工具会自动提取 `data.*_report` 字段，直接打印报告文本。

#### 全量分析（输出原始 JSON，供 render_report.py 管道使用）

```bash
./call_mcp.sh trading_agent '{"symbol":"688031","trade_date":"2026-07-08","analysts":["market","social","news","fundamentals"],"max_debate_rounds":1,"max_risk_discuss_rounds":1,"parallel_analysts":true,"detail":false}'
```

> `trading_agent` 会打印完整的内层 JSON 对象（包含 `success`/`ctx`/`data`），供 `render_report.py` 通过 stdin 管道接收。

### call_mcp.sh 的 SSE 解析逻辑

SSE 响应中包含多种行类型，脚本按以下方式过滤：

| SSE 行类型 | 示例 | 处理方式 |
|------------|------|----------|
| `event: message` | `event: message` | 忽略 |
| 通知消息 | `data: {"method":"notifications/message",...}` | 忽略（不含 `result`） |
| ping | `: ping - 2026-07-08...` | 忽略 |
| **最终结果** | `data: {"jsonrpc":"2.0","id":2,"result":{...}}` | **提取并解析** |

关键过滤命令：
```bash
grep '^data: {' | grep -i '"result"' | sed 's/^data: //' | tail -1
```
- `grep '^data: {'` — 只保留 JSON 数据行
- `grep -i '"result"'` — 只保留包含 `result` 的行（排除通知消息）
- `tail -1` — 取最后一条（确保是最终结果）

## 调用规范

根据用户意图，按以下方式处理远程 MCP 调用结果：

### 1. 获取工具列表 → 直接返回解析结果

当用户想看"工具有哪些"时，调用 `tools/list`，解析 SSE 响应中的工具有效列表后直接返回。

### 2. 服务健康检查 → 直接返回状态结果

当用户想看"服务是否正常"时，调用 `agent_status`，解析各组件状态后直接返回。

### 3. 调用单分析师 → 直接返回报告内容

当用户需要单维度分析时，根据需求调用对应工具并直接返回报告文本内容：
- 技术面 → `market_analyst`
- 基本面 → `fundamentals_analyst`
- 新闻 → `news_analyst`
- 情绪 → `social_analyst`

### 4. 全量综合分析 → 渲染为 HTML

当用户需要完整的投资分析决策时，调用 `trading_agent`（`detail: false`），将返回的 JSON 结果用 `render_report.py` 渲染为 HTML。

### render_report.py 使用方式

```bash
# 方式1: 管道渲染 -> 写入临时文件并用浏览器打开
./call_mcp.sh trading_agent '{"symbol":"688031","trade_date":"2026-07-08","detail":false}' | python3 render_report.py

# 方式2: 管道渲染 -> 输出到 stdout（供侧边栏预览 / artifacts create）
./call_mcp.sh trading_agent '{"symbol":"688031","trade_date":"2026-07-08","detail":false}' | python3 render_report.py --stdout

# 方式3: 管道渲染 -> 输出到指定文件
./call_mcp.sh trading_agent '{"symbol":"688031","trade_date":"2026-07-08","detail":false}' | python3 render_report.py -o /tmp/report.html

# 方式4: 从文件读取 JSON 渲染
cat result.json | python3 render_report.py --stdout
```

### render_report.py 的渲染逻辑

1. 从 stdin 读取 JSON（支持 `call_mcp.sh` 管道或文件重定向）
2. 调用 `extract_report_data()` 提取所有字段，处理嵌套对象：
   - `investment_debate` → `bull_history` / `bear_history` / `judge_decision`
   - `risk_debate` → `aggressive_history` / `conservative_history` / `neutral_history` / `judge_decision`（映射为 `risk_judge_decision`）
3. 读取同目录的 `template.html`
4. 将 JSON 数据中的各字段替换到模板占位符（同时兼容英文 `___MARKET_REPORT___` 和中文 `___技术分析报告内容___` 两种格式）
5. 未匹配的占位符自动清空
6. 根据输出模式写出 HTML

### template.html 的占位符体系

template.html 使用 JavaScript 对象 `tpl` 存储数据，占位符放在反引号字符串中：

```javascript
const tpl = {
  entity:               `分析主体：___COMPANY_NAME___ (___SYMBOL___)`,
  market_report:        `___MARKET_REPORT___`,
  fundamentals_report:  `___FUNDAMENTALS_REPORT___`,
  // ... 其余字段同理
};
```

render_report.py 做的是**文本替换**——把 `___MARKET_REPORT___` 替换为 JSON 中对应的值。替换后 JavaScript 的 `fillTemplate()` 函数将值填入 DOM 元素。

占位符对照表：

| 占位符 | JSON 来源 | 说明 |
|--------|----------|------|
| `___COMPANY_NAME___` | `data.company_name` 或 `ctx.company_name` | 公司名称 |
| `___SYMBOL___` | `ctx.symbol` | 股票代码 |
| `___MARKET_REPORT___` | `data.market_report` | 技术分析报告 |
| `___FUNDAMENTALS_REPORT___` | `data.fundamentals_report` | 基本面分析报告 |
| `___NEWS_REPORT___` | `data.news_report` | 新闻分析报告 |
| `___SENTIMENT_REPORT___` | `data.sentiment_report` | 情绪分析报告 |
| `___BULL_HISTORY___` | `data.investment_debate.bull_history` | 看涨研究员观点 |
| `___BEAR_HISTORY___` | `data.investment_debate.bear_history` | 看跌研究员观点 |
| `___JUDGE_DECISION___` | `data.investment_debate.judge_decision` | 研究主管裁决 |
| `___TRADER_INVESTMENT_PLAN___` | `data.trader_investment_plan` | 交易员投资计划 |
| `___AGGRESSIVE_HISTORY___` | `data.risk_debate.aggressive_history` | 激进风控员观点 |
| `___CONSERVATIVE_HISTORY___` | `data.risk_debate.conservative_history` | 保守风控员观点 |
| `___NEUTRAL_HISTORY___` | `data.risk_debate.neutral_history` | 中性风控员观点 |
| `___RISK_JUDGE_DECISION___` | `data.risk_debate.judge_decision` | 投资组合经理风险裁决 |
| `___INVESTMENT_PLAN___` | `data.investment_plan` | 最终投资计划 |
| `___FINAL_TRADE_DECISION___` | `data.final_trade_decision` | 最终交易决策 |

> 同时兼容中文占位符（如 `___技术分析报告内容___`），确保旧版本模板也能正常渲染。