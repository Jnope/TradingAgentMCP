from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import get_stock_data


@tool
def get_stock_data(
    symbol: Annotated[str, "6位A股代码，如 000001"],
    start_date: Annotated[str, "开始日期，YYYY-MM-DD"],
    end_date: Annotated[str, "结束日期，YYYY-MM-DD"],
) -> str:
    """
    获取A股行情数据（OHLCV），数据来源：timelyre 内部数据库。
    Args:
        symbol: 6位A股代码，如 000001
        start_date: 开始日期，YYYY-MM-DD
        end_date: 结束日期，YYYY-MM-DD
    Returns:
        str: 包含股票行情数据的格式化文本
    """
    return get_stock_data(symbol, start_date, end_date)
