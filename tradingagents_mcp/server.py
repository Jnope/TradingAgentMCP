"""
TradingAgents A股 MCP Agent Server

将多Agent协作分析引擎封装为 MCP Tools，
支持完整全流程和单分析师独立调用。

启动方式:
  stdio:    tradingagents-mcp          (或 python -m tradingagents_mcp)
  http:     MCP_TRANSPORT=streamable-http tradingagents-mcp
  check:    tradingagents-mcp check    (环境自检)
"""

import asyncio
import logging
import time
from typing import Optional

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession

from tradingagents_mcp.validators import (
    validate_symbol,
    normalize_date,
    nearest_trade_date,
    build_config,
    check_health,
    extract_full_result,
)
from tradingagents_mcp.shared_context import get_shared_ctx

logger = logging.getLogger("mcp_server")

mcp = FastMCP(
    "TradingAgents-A股",
    instructions="AI金融交易分析Agent — A股多Agent协作分析和单分析师独立调用",
)


_ANALYST_LABELS = {
    "market": "市场",
    "fundamentals": "基本面",
    "news": "新闻",
    "social": "社交情绪",
}


async def _run_single_analyst(
    analyst_type: str,
    symbol: str,
    trade_date: str,
    ctx: Context = None,
    extra_state: dict = None,
) -> dict:
    ctx_ = get_shared_ctx()
    label = _ANALYST_LABELS.get(analyst_type, analyst_type)

    if ctx:
        await ctx.info(f"[1/3] 正在初始化{label}分析师...")

    from langchain_core.messages import HumanMessage

    state = {
        "messages": [HumanMessage(content=f"请分析股票 {symbol}")],
        "company_of_interest": symbol,
        "trade_date": trade_date,
        f"{analyst_type}_tool_call_count": 0,
    }
    if extra_state:
        state.update(extra_state)

    analyst_map = {
        "market": ("create_market_analyst", "market_report"),
        "fundamentals": ("create_fundamentals_analyst", "fundamentals_report"),
        "news": ("create_news_analyst", "news_report"),
        "social": ("create_sentiment_analyst", "sentiment_report"),
    }

    _, report_key = analyst_map[analyst_type]

    from tradingagents.agents import (
        create_market_analyst,
        create_fundamentals_analyst,
        create_news_analyst,
        create_sentiment_analyst,
    )

    create_fn = {
        "market": create_market_analyst,
        "fundamentals": create_fundamentals_analyst,
        "news": create_news_analyst,
        "social": create_sentiment_analyst,
    }[analyst_type]

    node = create_fn(ctx_.quick_thinking_llm)

    if ctx:
        await ctx.info(f"[2/3] 正在获取 {symbol} 数据并执行{label}分析...")

    t1 = time.time()
    loop = asyncio.get_running_loop()
    result_state = await loop.run_in_executor(None, lambda: node(state))
    elapsed = round(time.time() - t1, 1)

    if ctx:
        await ctx.info(f"[3/3] {label}分析完成，耗时 {elapsed}s")

    report = result_state.get(report_key, "")

    return {
        "success": True,
        "symbol": symbol,
        "trade_date": trade_date,
        "analyst": analyst_type,
        "report": report,
    }


# ============================================================
# Tool 1: trading_agent
# ============================================================
@mcp.tool()
async def trading_agent(
    symbol: str,
    trade_date: str,
    analysts: Optional[list[str]] = None,
    max_debate_rounds: int = 1,
    max_risk_discuss_rounds: int = 1,
    parallel_analysts: Optional[bool] = None,
    ctx: Context[ServerSession, None] = None,
) -> dict:
    """AI金融交易分析Agent（完整流程）：执行多Agent协作分析，
    包含数据获取→多空辩论→风险评估→交易决策。

    仅支持A股(6位数字代码，如000001)。

    Args:
        symbol: A股股票代码，如000001
        trade_date: 交易日期 YYYY-MM-DD
        analysts: 分析师组合，默认 ["market","social","news","fundamentals"]
        max_debate_rounds: 多空辩论轮次
        max_risk_discuss_rounds: 风险辩论轮次
        parallel_analysts: 分析师是否并行执行，默认读取 MCP_PARALLEL_ANALYSTS 环境变量，未设置则并行
"""
    t0 = time.time()
    if analysts is None:
        analysts = ["market", "social", "news", "fundamentals"]

    try:
        symbol, market = validate_symbol(symbol)
        trade_date = nearest_trade_date(normalize_date(trade_date))
    except ValueError as e:
        return {"success": False, "error": str(e)}

    if ctx:
        await ctx.info(f"TradingAgent 开始分析: {symbol}({market}) @ {trade_date}")

    try:
        shared = get_shared_ctx()

        config = build_config()
        config["max_debate_rounds"] = max_debate_rounds
        config["max_risk_discuss_rounds"] = max_risk_discuss_rounds
        if parallel_analysts is not None:
            config["parallel_analysts"] = parallel_analysts

        ta = shared.get_graph(analysts, config=config)

        progress_callback = None
        if ctx:
            event_loop = asyncio.get_event_loop()
            def _on_progress(msg: str):
                asyncio.run_coroutine_threadsafe(ctx.info(msg), event_loop)
            progress_callback = _on_progress

        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(
            None, lambda: ta.propagate(symbol, trade_date)
        )

        from tradingagents.agents.utils.rating import parse_rating

        elapsed = round(time.time() - t0, 1)
        result = {
            "success": True,
            "symbol": symbol,
            "market": market,
            "trade_date": trade_date,
            "tool": "trading_agent",
            "analysts_used": analysts,
            "elapsed_seconds": elapsed,
            **extract_full_result(state),
        }

        return result

    except Exception as e:
        logger.error(f"trading_agent 分析失败: {e}", exc_info=True)
        return {"success": False, "error": str(e), "symbol": symbol, "elapsed_seconds": round(time.time() - t0, 1)}


# ============================================================
# Tool 2-5: 单分析师
# ============================================================
@mcp.tool()
async def market_analyst(
    symbol: str, trade_date: str, ctx: Context[ServerSession, None] = None,
) -> dict:
    """市场分析师Agent（独立运行）：获取A股行情数据并生成技术分析报告。

    分析内容：移动平均线、MACD、RSI、布林带、价格趋势、成交量。
    适合只需看技术面的场景，速度快（~30秒 vs 全流程3-5分钟）。

    Args:
        symbol: A股股票代码，如000001
        trade_date: 交易日期 YYYY-MM-DD
"""
    try:
        symbol, market = validate_symbol(symbol)
        trade_date = nearest_trade_date(normalize_date(trade_date))
    except ValueError as e:
        return {"success": False, "error": str(e)}

    t0 = time.time()
    try:
        result = await _run_single_analyst("market", symbol, trade_date, ctx)
        result["market"] = market
        result["elapsed_seconds"] = round(time.time() - t0, 1)
        return result
    except Exception as e:
        logger.error(f"market_analyst 失败: {e}", exc_info=True)
        return {"success": False, "error": str(e), "symbol": symbol, "elapsed_seconds": round(time.time() - t0, 1)}


@mcp.tool()
async def fundamentals_analyst(
    symbol: str, trade_date: str, ctx: Context[ServerSession, None] = None,
) -> dict:
    """基本面分析师Agent（独立运行）：获取PE/PB/ROE等财务数据并生成基本面报告。

    分析内容：估值指标、盈利能力、财务健康、行业对比。

    Args:
        symbol: A股股票代码，如000001
        trade_date: 交易日期 YYYY-MM-DD
"""
    try:
        symbol, market = validate_symbol(symbol)
        trade_date = nearest_trade_date(normalize_date(trade_date))
    except ValueError as e:
        return {"success": False, "error": str(e)}

    t0 = time.time()
    try:
        result = await _run_single_analyst("fundamentals", symbol, trade_date, ctx)
        result["market"] = market
        result["elapsed_seconds"] = round(time.time() - t0, 1)
        return result
    except Exception as e:
        logger.error(f"fundamentals_analyst 失败: {e}", exc_info=True)
        return {"success": False, "error": str(e), "symbol": symbol, "elapsed_seconds": round(time.time() - t0, 1)}


@mcp.tool()
async def news_analyst(
    symbol: str, trade_date: str, look_back_days: int = 7,
    ctx: Context[ServerSession, None] = None,
) -> dict:
    """新闻分析师Agent（独立运行）：获取股票相关新闻并生成分析报告。

    分析内容：重大新闻事件、政策影响、行业动态、潜在风险。

    Args:
        symbol: A股股票代码，如000001
        trade_date: 交易日期 YYYY-MM-DD
        look_back_days: 回看天数，默认7
"""
    try:
        symbol, market = validate_symbol(symbol)
        trade_date = nearest_trade_date(normalize_date(trade_date))
    except ValueError as e:
        return {"success": False, "error": str(e)}

    t0 = time.time()
    try:
        result = await _run_single_analyst(
            "news", symbol, trade_date, ctx,
            extra_state={"news_tool_call_count": 0},
        )
        result["market"] = market
        result["look_back_days"] = look_back_days
        result["elapsed_seconds"] = round(time.time() - t0, 1)
        return result
    except Exception as e:
        logger.error(f"news_analyst 失败: {e}", exc_info=True)
        return {"success": False, "error": str(e), "symbol": symbol, "elapsed_seconds": round(time.time() - t0, 1)}


@mcp.tool()
async def social_analyst(
    symbol: str, trade_date: str, ctx: Context[ServerSession, None] = None,
) -> dict:
    """社交媒体分析师Agent（独立运行）：获取社交平台情绪并生成分析报告。

    分析内容：投资者情绪、讨论热度、关键观点、多空倾向。

    Args:
        symbol: A股股票代码，如000001
        trade_date: 交易日期 YYYY-MM-DD
"""
    try:
        symbol, market = validate_symbol(symbol)
        trade_date = nearest_trade_date(normalize_date(trade_date))
    except ValueError as e:
        return {"success": False, "error": str(e)}

    t0 = time.time()
    try:
        result = await _run_single_analyst("social", symbol, trade_date, ctx)
        result["market"] = market
        result["elapsed_seconds"] = round(time.time() - t0, 1)
        return result
    except Exception as e:
        logger.error(f"social_analyst 失败: {e}", exc_info=True)
        return {"success": False, "error": str(e), "symbol": symbol, "elapsed_seconds": round(time.time() - t0, 1)}


# ============================================================
# Tool 6: agent_status
# ============================================================
@mcp.tool()
async def agent_status() -> dict:
    """查询当前Agent的配置状态、健康检查和支持的能力。
    适合在分析前检查环境是否就绪，或排查MCP连接问题。"""
    config = build_config()
    health = check_health()

    return {
        "success": True,
        "version": "1.0.0",
        "health": health,
        "supported_markets": ["A股"],
        "available_tools": {
            "trading_agent": "完整全流程分析（分析师→辩论→风险→决策，3-10分钟）",
            "market_analyst": "独立市场/技术分析（~30秒）",
            "fundamentals_analyst": "独立基本面分析（~30秒）",
            "news_analyst": "独立新闻分析（~30秒）",
            "social_analyst": "独立社交媒体情绪分析（~30秒）",
        },
        "data_sources": {
            "A股行情/基本面": "timelyre 内部数据库",
            "新闻/舆情": "akshare",
        },
        **config,
    }


from tradingagents_mcp.prompts import register_prompts
register_prompts(mcp)
