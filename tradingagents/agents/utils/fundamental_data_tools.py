from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import (
    get_fundamentals as _get_fundamentals,
    get_balance_sheet as _get_balance_sheet,
    get_cashflow as _get_cashflow,
    get_income_statement as _get_income_statement,
    get_money_flow as _get_money_flow,
)


@tool
def get_fundamentals(
    ticker: Annotated[str, "6位A股代码，如 000001"],
    curr_date: Annotated[str, "当前日期，YYYY-MM-DD"],
) -> str:
    """
    获取A股基本面概览（估值+盈利+成长+分红），数据来源：timelyre 内部数据库。
    Args:
        ticker: 6位A股代码
        curr_date: 当前日期，YYYY-MM-DD
    Returns:
        str: 包含基本面数据的格式化文本
    """
    return _get_fundamentals(ticker, curr_date)


@tool
def get_balance_sheet(
    ticker: Annotated[str, "6位A股代码，如 000001"],
    freq: Annotated[str, "报告频率: annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "当前日期，YYYY-MM-DD"] = None,
) -> str:
    """
    获取A股资产负债表，数据来源：timelyre 内部数据库。
    Args:
        ticker: 6位A股代码
        freq: 报告频率: annual/quarterly（默认 quarterly）
        curr_date: 当前日期，YYYY-MM-DD
    Returns:
        str: 包含资产负债表数据的格式化文本
    """
    return _get_balance_sheet(ticker, freq, curr_date)


@tool
def get_cashflow(
    ticker: Annotated[str, "6位A股代码，如 000001"],
    freq: Annotated[str, "报告频率: annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "当前日期，YYYY-MM-DD"] = None,
) -> str:
    """
    获取A股现金流量表，数据来源：timelyre 内部数据库。
    Args:
        ticker: 6位A股代码
        freq: 报告频率: annual/quarterly（默认 quarterly）
        curr_date: 当前日期，YYYY-MM-DD
    Returns:
        str: 包含现金流量表数据的格式化文本
    """
    return _get_cashflow(ticker, freq, curr_date)


@tool
def get_income_statement(
    ticker: Annotated[str, "6位A股代码，如 000001"],
    freq: Annotated[str, "报告频率: annual/quarterly"] = "quarterly",
    curr_date: Annotated[str, "当前日期，YYYY-MM-DD"] = None,
) -> str:
    """
    获取A股利润表，数据来源：timelyre 内部数据库。
    Args:
        ticker: 6位A股代码
        freq: 报告频率: annual/quarterly（默认 quarterly）
        curr_date: 当前日期，YYYY-MM-DD
    Returns:
        str: 包含利润表数据的格式化文本
    """
    return _get_income_statement(ticker, freq, curr_date)


@tool
def get_money_flow_tool(
    ticker: Annotated[str, "6位A股代码，如 000001"],
    start_date: Annotated[str, "开始日期，YYYY-MM-DD"],
    end_date: Annotated[str, "结束日期，YYYY-MM-DD"],
) -> str:
    """
    获取A股资金流向数据，数据来源：timelyre 内部数据库。
    Args:
        ticker: 6位A股代码
        start_date: 开始日期，YYYY-MM-DD
        end_date: 结束日期，YYYY-MM-DD
    Returns:
        str: 包含资金流向数据的格式化文本
    """
    return _get_money_flow(ticker, start_date, end_date)
