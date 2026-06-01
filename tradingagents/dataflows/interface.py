"""
A 股统一数据入口

数据源：timelyre（行情/基本面） + akshare（新闻/舆情）
所有方法直接调用对应查询模块，无降级逻辑。
"""

import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from .providers.china.internal_queries import (
    get_daily_kline,
    get_money_flow as _get_money_flow,
)
from .providers.china.internal_code_mapper import to_internal_code
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

logger = logging.getLogger(__name__)


# ==================== 行情数据 ====================

def get_stock_data(symbol: str, start_date: str, end_date: str) -> str:
    """获取 A 股 K 线数据（timelyre stock_bar_1day）"""
    logger.info("get_stock_data: symbol=%s start=%s end=%s", symbol, start_date, end_date)
    df = get_daily_kline(symbol, start_date, end_date)

    if df.empty:
        logger.warning("get_stock_data: no data returned for %s", symbol)
        return f"未找到 {symbol} 在 {start_date} 至 {end_date} 的行情数据"

    df = df.rename(columns={
        "trade_day": "date",
        "volume": "vol",
        "turnover": "amount",
    })
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
    if "pct_change" not in df.columns and "close" in df.columns:
        df["pct_change"] = df["close"].pct_change() * 100.0

    header = f"# A股行情数据: {symbol} ({start_date} ~ {end_date})\n"
    header += f"# 数据来源: TransMatrix 内部数据库\n"
    header += f"# 记录数: {len(df)}\n"
    header += f"# 获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    result = header + df.to_csv(index=False)
    logger.info("get_stock_data: symbol=%s returned %d rows, %d chars", symbol, len(df), len(result))
    return result


# ==================== 技术指标 ====================

def get_technical_indicators(symbol: str, indicator: str, curr_date: str, look_back_days: int = 30) -> str:
    """获取技术指标数据（基于 timelyre K 线本地计算）"""
    logger.info("get_technical_indicators: symbol=%s indicator=%s date=%s", symbol, indicator, curr_date)
    from .technical.stockstats import calculate_indicators
    result = calculate_indicators(symbol, indicator, curr_date, look_back_days)
    logger.info("get_technical_indicators: symbol=%s result_length=%d", symbol, len(result) if result else 0)
    return result


# ==================== 基本面数据 ====================

def get_fundamentals(symbol: str, curr_date: str) -> str:
    """获取公司基本面概览（估值+盈利+成长+分红），timelyre 数据"""
    logger.info("get_fundamentals: symbol=%s date=%s", symbol, curr_date)
    return get_fundamentals_overview(symbol, curr_date)


def get_balance_sheet(symbol: str, freq: str = "quarterly", curr_date: str = None) -> str:
    """获取资产负债表，timelyre balance 表"""
    logger.info("get_balance_sheet: symbol=%s freq=%s", symbol, freq)
    return get_balance_sheet_data(symbol, freq, curr_date)


def get_cashflow(symbol: str, freq: str = "quarterly", curr_date: str = None) -> str:
    """获取现金流量表，timelyre cashflow 表"""
    logger.info("get_cashflow: symbol=%s freq=%s", symbol, freq)
    return get_cashflow_data(symbol, freq, curr_date)


def get_income_statement(symbol: str, freq: str = "quarterly", curr_date: str = None) -> str:
    """获取利润表，timelyre income 表"""
    logger.info("get_income_statement: symbol=%s freq=%s", symbol, freq)
    return get_income_statement_data(symbol, freq, curr_date)


def get_money_flow(symbol: str, start_date: str, end_date: str) -> str:
    """获取资金流向，timelyre stock_money_flow 表"""
    logger.info("get_money_flow: symbol=%s start=%s end=%s", symbol, start_date, end_date)
    df = _get_money_flow(symbol, start_date, end_date)
    if df.empty:
        logger.warning("get_money_flow: no data for %s", symbol)
        return ""
    latest = df.iloc[-1]
    report = f"{symbol} 资金流向 ({latest.get('trade_day', '')})\n\n"
    report += f"   涨跌幅: {latest.get('change_pct', 'N/A')}%\n"
    report += f"   主力净额: {latest.get('net_amount_main', 'N/A')}万\n"
    report += f"   主力净占比: {latest.get('net_pct_main', 'N/A')}%\n"
    report += f"   超大单净额: {latest.get('net_amount_xl', 'N/A')}万\n"
    report += f"   大单净额: {latest.get('net_amount_l', 'N/A')}万\n"
    report += f"   中单净额: {latest.get('net_amount_m', 'N/A')}万\n"
    report += f"   小单净额: {latest.get('net_amount_s', 'N/A')}万\n"
    return report


# ==================== 新闻数据 ====================

def get_news(symbol: str, curr_date: str, look_back_days: int = 7) -> str:
    """获取个股新闻（akshare）"""
    logger.info("get_news: symbol=%s date=%s look_back=%d", symbol, curr_date, look_back_days)
    return get_stock_news(symbol, look_back_days)


def get_global_news(curr_date: str, look_back_days: int = None, limit: int = None) -> str:
    """获取宏观财经新闻（akshare）"""
    logger.info("get_global_news: date=%s look_back=%s limit=%s", curr_date, look_back_days, limit)
    return get_macro_news()


# ==================== 社交情绪 ====================

def get_sentiment(symbol: str) -> str:
    """获取社交舆情（akshare 股吧）"""
    logger.info("get_sentiment: symbol=%s", symbol)
    return get_stock_sentiment(symbol)
