---
name: trading-agents
description: |
  A股AI金融交易分析MCP工具tradingagents使用的文档；
  用于对A股执行完整多Agent协作分析(市场/情绪/新闻/基本面→多空辩论→风险讨论→最终决策)，或单独查询技术面即市场/基本面/新闻/情绪；
  仅支持A股(6位数字代码)。
  触发词：分析股票、交易分析、股票分析、金融分析、A股分析、技术面分析、市场分析、基本面分析、新闻分析、情绪分析、
  交易决策、投资建议
license: MIT
compatibility: opencode
metadata:
  category: finance
  tools: tradingagents
  market: A股
  data_sources: timelyre+akshare
---

# TradingAgents — A股AI金融交易分析

仅支持A股，股票代码为6位数字（如 `000001`、`600519`），用于调用tradingagents MCP，**不要对输出结果进行解析，分析结束后反馈结束即可**。

## 意图 → 工具映射

| 用户意图 | 工具 | 耗时     |
|---------|------|--------|
| 全面分析/投资建议/要不要买 | `trading_agent` | 3-30分钟 |
| 技术面/市场/走势/K线 | `market_analyst` | 1-10分钟 |
| 估值/基本面/PE | `fundamentals_analyst` | 1-10分钟 |
| 新闻/利好利空 | `news_analyst` | 1-10分钟 |
| 情绪/大家怎么看 | `social_analyst` | 1-10分钟 |
| 你能做什么/环境检查 | `agent_status` | <10秒   |

模糊表述（如"分析一下"）必须询问确认类型，不得自行选择。

## 调用前确认

调用任何分析工具前，必须依次确认以下三项（**若用户已在上下文中明确提供某项信息，则跳过该项确认，仅确认缺失项**）：

1. **股票代码**：6位数字。中文股票名需确认对应代码（如"茅台"→确认"600519"）
2. **分析日期**：YYYY-MM-DD 格式。未指定则询问，"今天"/"昨天"自动转换
3. **分析类型**：未明确时必须询问确认

调用任何工具前必须告知用户："全流程分析需要 {least-max} 分钟，请耐心等待"; least/max为工具时间范围

## 环境检查

首次使用时调用 `agent_status()` 确认环境就绪：
- `health.llm_api_key` 含 "missing" → 提示检查 API Key 配置
- `health.timelyre` 不为 "ok" → 提示检查数据库连接配置

## 调用行为约束（严格遵守）

1. **等待完整返回**：调用工具后必须静默等待完整 JSON 返回，期间不做任何操作
2. **禁止中断重试**：不得因等待时间长而中断、取消或重新调用同一工具
3. **禁止假设失败**：超出预计调用时间，不代表调用失败
4. **禁止补调**：不得在收到结果后再调用其他工具"补充获取"数据（如调完 `market_analyst` 又调 `trading_agent`）
5. **不自动重试**: 无论是否失败，不自动重试

## 结果输出

- `trading_agent`、`market_analyst`、`market_analyst`、`social_analyst`工具返回结果后，向用户反馈分析结束即可，**无须输出或解析对应结果**
- 错误时结果结果中包含 `error` 属性值，需将原因展示给用户
