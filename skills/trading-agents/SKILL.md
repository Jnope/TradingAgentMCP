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

仅支持A股，股票代码为6位数字（如 `000001`、`600519`）。

## 调用行为约束（严格遵守）

1. **等待完整返回**：调用工具后必须静默等待完整 JSON 返回，期间不做任何操作
2. **禁止中断重试**：不得因等待时间长而中断、取消或重新调用同一工具
3. **禁止补调**：不得在收到结果后再调用其他工具"补充获取"数据（如调完 `market_analyst` 又调 `trading_agent`）
4. **禁止假设失败**：耗时 3-30 分钟是 `trading_agent` 的正常行为，1-10 分钟是单分析师的正常行为，不代表调用失败
5. **检查 success 字段**：返回 `success: true` 直接使用 元数据；返回 `success: false` 读取 `error` 报告用户，不自动重试

## 数据输出强制约束（最高优先级）

1. **原样透传**：收到 MCP 工具返回的 JSON 后，必须将其作为代码块完整输出，严禁提取字段、生成摘要、改写结构或调用 `.toString()`
2. **禁止嵌套转义**：不得对返回的 JSON 字符串进行二次序列化（避免出现 `"{\"success\":true}"` 这种双重引号格式）
3. **禁止混合输出**：不要在 JSON 代码块前后添加任何解释性文字、问候语或分析总结。你的唯一任务是将原始 JSON 放入 ```json 代码块中返回给前端
4. **错误处理例外**：仅当 `success: false` 时，才允许读取 `error` 字段并以纯文本形式向用户报告错误原因；`success: true` 时必须严格遵循上述透传规则
5. **前端契约**：前端依赖完整的 JSON 结构进行渲染，任何字段缺失、类型变更或结构拍平都会导致系统崩溃

## 调用前确认

调用任何分析工具前，必须依次确认以下三项（每项单独确认，不得跳过或合并）：

1. **股票代码**：6位数字。中文股票名需确认对应代码（如"茅台"→确认"600519"）
2. **分析日期**：YYYY-MM-DD 格式。未指定则询问，"今天"/"昨天"自动转换
3. **分析类型**：未明确时必须询问确认

## 意图 → 工具映射

| 用户意图 | 工具 | 耗时     |
|---------|------|--------|
| 全面分析/投资建议/要不要买 | `trading_agent` | 3-30分钟 |
| 技术面/走势/K线 | `market_analyst` | 1-10分钟 |
| 估值/基本面/PE | `fundamentals_analyst` | 1-10分钟 |
| 新闻/利好利空 | `news_analyst` | 1-10分钟 |
| 情绪/大家怎么看 | `social_analyst` | 1-10分钟 |
| 你能做什么/环境检查 | `agent_status` | <10秒   |

模糊表述（如"分析一下"）必须询问确认类型，不得自行选择。

调用 `trading_agent` 前必须告知用户："全流程分析需要 3-30 分钟，请耐心等待"

## 用户交互约束

- 调用 `trading_agent` 前，必须先发送一条纯文本消息："全流程分析需要 3-30 分钟，请耐心等待"，然后再发起工具调用
- 工具返回后，仅输出 JSON 代码块，不再追加任何等待结束提示或结果解读

## 返回数据结构声明（仅供校验，禁止拆解）

所有工具返回统一 JSON Schema，以下为关键字段定义（AI 无需理解内容，仅需确保结构完整透传）：

- `success` (bool) — 判断调用是否成功
- `error` (str) — 失败时的错误信息
- `ctx.company_name` (str) — 公司名称（如"贵州茅台"）
- `ctx.symbol` (str) — 股票代码
- `ctx.trade_date` (str) — 交易日期
- `ctx.elapsed_seconds` (float) — 耗时
- `data` (object) — 工具返回的具体数据

`trading_agent` 的 `data` 包含：`company_name`、`market_report`、`fundamentals_report`、`sentiment_report`、`news_report`、`investment_debate`、`trader_investment_plan`、`risk_debate`、`investment_plan`、`final_trade_decision`

⚠️ 注意：以上字段说明仅用于验证 JSON 完整性，绝不允许基于此说明对数据进行筛选、重组或自然语言转述。

## 环境检查

首次使用时调用 `agent_status()` 确认环境就绪：
- `health.llm_api_key` 含 "missing" → 提示检查 API Key 配置
- `health.timelyre` 不为 "ok" → 提示检查数据库连接配置
