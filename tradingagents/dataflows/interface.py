"""
A 股统一数据入口

数据源：timelyre（行情/基本面） + akshare（新闻/舆情）
所有方法直接调用对应 provider，无降级逻辑。
"""

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from .providers.china.internal import get_internal_provider
from .providers.china.internal_fundamentals_data import (
    get_fundamentals_overview,
    get_balance_sheet_data,
    get_cashflow_data,
    get_income_statement_data,
)
from .providers.china.akshare_news import (
    get_stock_news,
    get_stock_sentiment,
    get_macro_news,
)
from .config import get_config


# ==================== 行情数据 ====================

def get_stock_data(symbol: str, start_date: str, end_date: str) -> str:
    """获取 A 股 K 线数据（timelyre stock_bar_1day）

    Args:
        symbol: 6位A股代码
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD

    Returns:
        格式化的 K 线数据 CSV
    """
    provider = get_internal_provider()
    df = provider.get_stock_data(symbol, start_date, end_date)

    if df.empty:
        return f"未找到 {symbol} 在 {start_date} 至 {end_date} 的行情数据"

    header = f"# A股行情数据: {symbol} ({start_date} ~ {end_date})\n"
    header += f"# 数据来源: TransMatrix 内部数据库\n"
    header += f"# 记录数: {len(df)}\n"
    header += f"# 获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    return header + df.to_csv(index=False)


# ==================== 技术指标 ====================

def get_technical_indicators(symbol: str, indicator: str, curr_date: str, look_back_days: int = 30) -> str:
    """获取技术指标数据（基于 timelyre K 线本地计算）

    Args:
        symbol: 6位A股代码
        indicator: 技术指标名称（如 rsi, macd, close_50_sma 等）
        curr_date: 当前交易日 YYYY-MM-DD
        look_back_days: 回看天数

    Returns:
        格式化的技术指标报告
    """
    from .technical.stockstats import calculate_indicators

    return calculate_indicators(symbol, indicator, curr_date, look_back_days)


# ==================== 基本面数据 ====================

def get_fundamentals(symbol: str, curr_date: str) -> str:
    """获取公司基本面概览（估值+盈利+成长+分红），timelyre 数据

    Args:
        symbol: 6位A股代码
        curr_date: 当前日期 YYYY-MM-DD

    Returns:
        基本面概览文本
    """
    return get_fundamentals_overview(symbol, curr_date)


def get_balance_sheet(symbol: str, freq: str = "quarterly", curr_date: str = None) -> str:
    """获取资产负债表，timelyre balance 表

    Args:
        symbol: 6位A股代码
        freq: annual/quarterly
        curr_date: 当前日期 YYYY-MM-DD

    Returns:
        资产负债表文本
    """
    return get_balance_sheet_data(symbol, freq, curr_date)


def get_cashflow(symbol: str, freq: str = "quarterly", curr_date: str = None) -> str:
    """获取现金流量表，timelyre cashflow 表

    Args:
        symbol: 6位A股代码
        freq: annual/quarterly
        curr_date: 当前日期 YYYY-MM-DD

    Returns:
        现金流量表文本
    """
    return get_cashflow_data(symbol, freq, curr_date)


def get_income_statement(symbol: str, freq: str = "quarterly", curr_date: str = None) -> str:
    """获取利润表，timelyre income 表

    Args:
        symbol: 6位A股代码
        freq: annual/quarterly
        curr_date: 当前日期 YYYY-MM-DD

    Returns:
        利润表文本
    """
    return get_income_statement_data(symbol, freq, curr_date)


def get_money_flow(symbol: str, start_date: str, end_date: str) -> str:
    """获取资金流向，timelyre stock_money_flow 表

    Args:
        symbol: 6位A股代码
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD

    Returns:
        资金流向文本
    """
    provider = get_internal_provider()
    return provider.get_money_flow(symbol, start_date, end_date)


# ==================== 新闻数据 ====================

def get_news(symbol: str, curr_date: str, look_back_days: int = 7) -> str:
    """获取个股新闻（akshare）

    Args:
        symbol: 6位A股代码
        curr_date: 当前日期 YYYY-MM-DD
        look_back_days: 回看天数

    Returns:
        新闻文本
    """
    return get_stock_news(symbol, look_back_days)


def get_global_news(curr_date: str, look_back_days: int = None, limit: int = None) -> str:
    """获取宏观财经新闻（akshare）

    Args:
        curr_date: 当前日期 YYYY-MM-DD
        look_back_days: 回看天数（暂未使用）
        limit: 返回条数限制（暂未使用）

    Returns:
        宏观新闻文本
    """
    return get_macro_news()


# ==================== 社交情绪 ====================

def get_sentiment(symbol: str) -> str:
    """获取社交舆情（akshare 股吧）

    Args:
        symbol: 6位A股代码

    Returns:
        舆情文本
    """
    return get_stock_sentiment(symbol)
