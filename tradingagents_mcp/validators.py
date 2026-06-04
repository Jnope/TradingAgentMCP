"""
A股参数校验、配置构建、健康检查
"""

import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import pandas as pd


_CN_STOCK_NAME_MAP = {
    "茅台": "600519", "贵州茅台": "600519",
    "平安银行": "000001",
    "招商银行": "600036",
    "五粮液": "000858",
    "宁德时代": "300750",
    "比亚迪": "002594",
    "工商银行": "601398",
    "中国平安": "601318",
    "美的集团": "000333",
    "格力电器": "000651",
    "中信证券": "600030",
    "海康威视": "002415",
    "隆基绿能": "601012",
    "中国中免": "601888",
    "药明康德": "603259",
    "紫金矿业": "601899",
    "长江电力": "600900",
    "中国移动": "600941",
    "中国石油": "601857",
    "中国神华": "601088",
}

_CN_INDEX_MAP = {
    "沪深300": "000300", "沪深300指数": "000300",
    "上证50": "000016",
    "中证500": "000905",
    "创业板指": "399006",
    "上证指数": "000001",
    "深证成指": "399001",
    "科创50": "000688",
}


def resolve_stock_name(name: str) -> Optional[str]:
    if not name:
        return None
    return _CN_STOCK_NAME_MAP.get(name) or _CN_INDEX_MAP.get(name)


def resolve_company_name(symbol: str) -> str:
    """根据6位股票代码查询公司名称，查询失败返回空字符串。"""
    try:
        from tradingagents.dataflows.providers.china.internal_queries import get_stock_info
        info = get_stock_info(symbol)
        if info and info.get("name"):
            return info["name"]
    except Exception:
        pass
    return symbol


def validate_symbol(symbol: str) -> Tuple[str, str]:
    if not symbol or not symbol.strip():
        raise ValueError("股票代码不能为空")

    symbol = symbol.strip()

    resolved = resolve_stock_name(symbol)
    if resolved:
        symbol = resolved

    if re.match(r'^\d{6}$', symbol):
        market = "A股"
    else:
        raise ValueError(
            f"无法识别股票代码 '{symbol}'。"
            "A股请用6位数字(如000001)"
        )

    return symbol, market


def normalize_date(date_str: str) -> str:
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")

    date_str = date_str.strip()

    aliases = {
        "今天": datetime.now(),
        "昨天": _prev_trading_day(1),
        "前天": _prev_trading_day(2),
    }
    if date_str in aliases:
        return aliases[date_str].strftime("%Y-%m-%d")

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass

    raise ValueError(f"日期格式无效 '{date_str}'，请使用 YYYY-MM-DD 格式")


def nearest_trade_date(date_str: str) -> str:
    from tradingagents_mcp.trade_calendar import get_trade_dates, _llm_judge_trade_date

    try:
        dt = pd.Timestamp(date_str)
    except Exception:
        return date_str

    trade_dates = get_trade_dates()

    if trade_dates:
        for _ in range(30):
            ds = dt.strftime("%Y-%m-%d")
            if ds in trade_dates:
                return ds
            dt = dt - pd.Timedelta(days=1)
        return date_str

    return _llm_judge_trade_date(date_str)


def build_config() -> dict:
    from tradingagents.default_config import DEFAULT_CONFIG

    config = DEFAULT_CONFIG.copy()
    env_map = {
        "MCP_LLM_PROVIDER": ("llm_provider", str),
        "MCP_DEEP_THINK_LLM": ("deep_think_llm", str),
        "MCP_QUICK_THINK_LLM": ("quick_think_llm", str),
        "MCP_BACKEND_URL": ("backend_url", str),
        "MCP_ONLINE_NEWS": ("online_news", lambda v: v.lower() == "true"),
        "MCP_MAX_DEBATE_ROUNDS": ("max_debate_rounds", int),
        "MCP_MAX_RISK_DISCUSS_ROUNDS": ("max_risk_discuss_rounds", int),
        "MCP_QUICK_PROVIDER": ("quick_provider", str),
        "MCP_DEEP_PROVIDER": ("deep_provider", str),
        "MCP_QUICK_BACKEND_URL": ("quick_backend_url", str),
        "MCP_DEEP_BACKEND_URL": ("deep_backend_url", str),
        "MCP_QUICK_API_KEY": ("quick_api_key", str),
        "MCP_DEEP_API_KEY": ("deep_api_key", str),
        "MCP_PARALLEL_ANALYSTS": ("parallel_analysts", lambda v: v.lower() == "true"),
    }
    for env_key, (config_key, type_fn) in env_map.items():
        val = os.getenv(env_key)
        if val is not None:
            config[config_key] = type_fn(val)

    model_param_map = {
        "MCP_DEEP_MAX_TOKENS": ("deep_model_config", "max_tokens", int),
        "MCP_QUICK_MAX_TOKENS": ("quick_model_config", "max_tokens", int),
        "MCP_DEEP_TEMPERATURE": ("deep_model_config", "temperature", float),
        "MCP_QUICK_TEMPERATURE": ("quick_model_config", "temperature", float),
        "MCP_DEEP_TIMEOUT": ("deep_model_config", "timeout", int),
        "MCP_QUICK_TIMEOUT": ("quick_model_config", "timeout", int),
    }
    for env_key, (config_key, param_key, type_fn) in model_param_map.items():
        val = os.getenv(env_key)
        if val is not None:
            config.setdefault(config_key, {})[param_key] = type_fn(val)

    provider_key_fallback = {
        "openai": ("OPENAI_API_KEY", "openai_api_key"),
        "dashscope": ("DASHSCOPE_API_KEY", "dashscope_api_key"),
        "alibaba": ("DASHSCOPE_API_KEY", "dashscope_api_key"),
        "google": ("GOOGLE_API_KEY", "google_api_key"),
        "anthropic": ("ANTHROPIC_API_KEY", "anthropic_api_key"),
        "deepseek": ("DEEPSEEK_API_KEY", "deepseek_api_key"),
        "siliconflow": ("SILICONFLOW_API_KEY", "siliconflow_api_key"),
        "openrouter": ("OPENROUTER_API_KEY", "openrouter_api_key"),
        "ollama": (None, None),
        "zhipu": ("ZHIPU_API_KEY", "zhipu_api_key"),
        "qianfan": ("QIANFAN_API_KEY", "qianfan_api_key"),
        "custom_openai": ("CUSTOM_OPENAI_API_KEY", "custom_openai_api_key"),
    }
    provider = config.get("llm_provider", "").lower()
    fallback = provider_key_fallback.get(provider)
    if fallback and fallback[0]:
        env_var, _ = fallback
        quick_key = config.get("quick_api_key")
        deep_key = config.get("deep_api_key")
        if not quick_key and not deep_key:
            env_val = os.getenv(env_var)
            if env_val:
                config.setdefault("quick_api_key", env_val)
                config.setdefault("deep_api_key", env_val)

    return config


def check_health() -> dict:
    config = build_config()
    health = {"mcp_server": "ok"}

    llm_provider = config.get("llm_provider", "").lower()
    key_map = {
        "openai": "OPENAI_API_KEY",
        "dashscope": "DASHSCOPE_API_KEY",
        "alibaba": "DASHSCOPE_API_KEY",
        "google": "GOOGLE_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "siliconflow": "SILICONFLOW_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "zhipu": "ZHIPU_API_KEY",
        "qianfan": "QIANFAN_API_KEY",
        "custom_openai": "CUSTOM_OPENAI_API_KEY",
    }
    has_config_key = bool(config.get("quick_api_key") or config.get("deep_api_key"))
    expected_key = key_map.get(llm_provider)
    if has_config_key:
        expected_key = None
    if expected_key and not os.getenv(expected_key):
        health["llm_api_key"] = f"missing: {expected_key}"
    else:
        health["llm_api_key"] = "ok"

    try:
        import akshare
        health["akshare"] = "ok"
    except ImportError:
        health["akshare"] = "not_installed"

    try:
        from tradingagents.dataflows.providers.china.internal_queries import health_check
        health["timelyre"] = "ok" if health_check() else "unavailable"
    except ImportError:
        health["timelyre"] = "not_installed"
    except Exception as e:
        health["timelyre"] = f"error: {e}"

    return health


def _prev_trading_day(n: int = 1) -> datetime:
    from tradingagents_mcp.trade_calendar import get_trade_dates

    trade_dates = get_trade_dates()
    dt = datetime.now()

    if trade_dates:
        count = 0
        while count < n:
            dt = dt - timedelta(days=1)
            if dt.strftime("%Y-%m-%d") in trade_dates:
                count += 1
        return dt

    count = 0
    while count < n:
        dt = dt - timedelta(days=1)
        if dt.weekday() < 5:
            count += 1
    return dt


_SERVER_NAME = "TradingAgents"


def build_response(
    *,
    tool: str,
    success: bool,
    error: str = "",
    symbol: str = "",
    market: str = "",
    company_name: str = "",
    trade_date: str = "",
    analysts_used: list = None,
    elapsed_seconds: float = 0.0,
    data: dict = None,
) -> dict:
    ctx: Dict[str, Any] = {
        "server_name": _SERVER_NAME,
        "tool": tool,
        "elapsed_seconds": elapsed_seconds,
    }
    if symbol:
        ctx["symbol"] = symbol
    if market:
        ctx["market"] = market
    if company_name:
        ctx["company_name"] = company_name
    if trade_date:
        ctx["trade_date"] = trade_date
    if analysts_used is not None:
        ctx["analysts_used"] = analysts_used

    return {
        "success": success,
        "error": error,
        "ctx": ctx,
        "data": data or {},
    }


def _sanitize_quotes(text: str) -> str:
    return text.replace('"', "'").replace("\u201c", "\u300c").replace("\u201d", "\u300d")


def _summarize_text(llm, text: str, role_hint: str, max_length: int = 1000) -> str:
    if not text or len(text) <= max_length:
        return _sanitize_quotes(text)
    prompt = (
        f"请将以下{role_hint}浓缩为简短摘要（200字以内），保留核心结论和关键数据，不要添加额外解释：\n\n{text}\n\n"
        "重要：摘要中绝对不要使用英文双引号(\")，请用中文单引号或「」代替。"
    )
    try:
        resp = llm.invoke(prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)
        return _sanitize_quotes(content)
    except Exception:
        return _sanitize_quotes(text[:max_length]) + "..."


def extract_full_result(state: dict, llm=None) -> dict:
    result = {}
    company_name = state.get("company_name", "")
    if company_name:
        result["company_name"] = company_name

    summarize = lambda text, hint: _summarize_text(llm, text, hint) if llm else _sanitize_quotes(text)

    report_hints = {
        "market_report": "市场技术分析报告",
        "fundamentals_report": "基本面分析报告",
        "sentiment_report": "社交媒体情绪报告",
        "news_report": "新闻分析报告",
    }
    for key, hint in report_hints.items():
        raw = state.get(key, "")
        result[key] = summarize(raw, hint) if raw else ""

    debate = state.get("investment_debate_state") or {}
    result["investment_debate"] = {
        "bull_history": summarize(debate.get("bull_history", ""), "看涨分析师辩论发言"),
        "bear_history": summarize(debate.get("bear_history", ""), "看跌分析师辩论发言"),
        "judge_decision": summarize(debate.get("judge_decision", ""), "多空辩论后研究主管的裁决发言"),
    }

    result["trader_investment_plan"] = summarize(
        state.get("trader_investment_plan", ""), "交易员投资计划"
    )

    risk = state.get("risk_debate_state") or {}
    result["risk_debate"] = {
        "aggressive_history": summarize(risk.get("aggressive_history", ""), "激进风险分析师辩论发言"),
        "conservative_history": summarize(risk.get("conservative_history", ""), "保守风险分析师辩论发言"),
        "neutral_history": summarize(risk.get("neutral_history", ""), "中性风险分析师辩论发言"),
        "judge_decision": _sanitize_quotes(risk.get("judge_decision", "")),
    }

    result["investment_plan"] = summarize(
        state.get("investment_plan", ""), "投资计划"
    )
    result["final_trade_decision"] = _sanitize_quotes(state.get("final_trade_decision", ""))

    return result


def extract_detail_result(state: dict) -> dict:
    result = {}
    company_name = state.get("company_name", "")
    if company_name:
        result["company_name"] = company_name
    for key in ["market_report", "fundamentals_report", "sentiment_report", "news_report"]:
        result[key] = _sanitize_quotes(state.get(key, ""))

    debate = state.get("investment_debate_state") or {}
    result["investment_debate"] = {
        "bull_history": _sanitize_quotes(debate.get("bull_history", "")),
        "bear_history": _sanitize_quotes(debate.get("bear_history", "")),
        "judge_decision": _sanitize_quotes(debate.get("judge_decision", "")),
    }

    result["trader_investment_plan"] = _sanitize_quotes(state.get("trader_investment_plan", ""))

    risk = state.get("risk_debate_state") or {}
    result["risk_debate"] = {
        "aggressive_history": _sanitize_quotes(risk.get("aggressive_history", "")),
        "conservative_history": _sanitize_quotes(risk.get("conservative_history", "")),
        "neutral_history": _sanitize_quotes(risk.get("neutral_history", "")),
        "judge_decision": _sanitize_quotes(risk.get("judge_decision", "")),
    }

    result["investment_plan"] = _sanitize_quotes(state.get("investment_plan", ""))
    result["final_trade_decision"] = _sanitize_quotes(state.get("final_trade_decision", ""))

    return result


def calc_period_stats(data) -> dict:
    if not data or len(data) < 2:
        return {"total_return": None, "max_drawdown": None, "volatility": None}

    closes = []
    for row in data:
        c = row.get("close") or row.get("Close")
        if c is not None:
            try:
                closes.append(float(c))
            except (ValueError, TypeError):
                continue

    if len(closes) < 2:
        return {"total_return": None, "max_drawdown": None, "volatility": None}

    total_return = round((closes[-1] / closes[0] - 1) * 100, 2)

    peak = closes[0]
    max_dd = 0.0
    for c in closes:
        if c > peak:
            peak = c
        dd = (c / peak - 1) * 100
        if dd < max_dd:
            max_dd = dd
    max_drawdown = round(max_dd, 2)

    import statistics
    daily_returns = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes))]
    if len(daily_returns) >= 2:
        vol = round(statistics.stdev(daily_returns) * (252 ** 0.5) * 100, 2)
    else:
        vol = None

    return {"total_return": total_return, "max_drawdown": max_drawdown, "volatility": vol}


def extract_data_points(data, metrics: list, max_points: int = 60) -> list:
    if not data:
        return []

    metric_key_map = {k.lower(): k for k in data[0].keys()} if data else {}
    rows = []
    for row in data:
        point = {}
        date_val = row.get("date") or row.get("trade_date") or row.get("Date")
        point["date"] = str(date_val) if date_val else ""
        for m in metrics:
            key = metric_key_map.get(m.lower(), m)
            val = row.get(key)
            if val is not None:
                try:
                    point[m] = round(float(val), 4)
                except (ValueError, TypeError):
                    point[m] = val
        rows.append(point)

    if len(rows) > max_points:
        step = len(rows) / max_points
        return [rows[int(i * step)] for i in range(max_points)]
    return rows
