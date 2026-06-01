from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import get_technical_indicators


@tool
def get_indicators(
    symbol: Annotated[str, "6位A股代码，如 000001"],
    indicator: Annotated[str, "技术指标名称，如 rsi, macd, close_50_sma。可逗号分隔多个指标，每个指标调用一次。"],
    curr_date: Annotated[str, "当前交易日，YYYY-MM-DD"],
    look_back_days: Annotated[int, "回看天数"] = 30,
) -> str:
    """
    获取A股技术指标数据（MA/MACD/RSI/BOLL等），基于 timelyre K 线本地计算。
    Args:
        symbol: 6位A股代码，如 000001
        indicator: 技术指标名称，如 rsi, macd, close_50_sma
        curr_date: 当前交易日，YYYY-MM-DD
        look_back_days: 回看天数，默认30
    Returns:
        str: 包含技术指标数据的格式化文本
    """
    indicators = [i.strip().lower() for i in indicator.split(",") if i.strip()]
    results = []
    for ind in indicators:
        try:
            results.append(get_technical_indicators(symbol, ind, curr_date, look_back_days))
        except ValueError as e:
            results.append(str(e))
    return "\n\n".join(results)
