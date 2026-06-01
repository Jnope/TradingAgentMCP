from langchain_core.tools import tool
from typing import Annotated, Optional
from tradingagents.dataflows.interface import get_news as _get_news, get_global_news as _get_global_news


@tool
def get_news(
    ticker: Annotated[str, "6位A股代码，如 000001"],
    start_date: Annotated[str, "开始日期，YYYY-MM-DD"],
    end_date: Annotated[str, "结束日期，YYYY-MM-DD"],
) -> str:
    """
    获取A股个股新闻数据，数据来源：akshare（东方财富/新浪财经）。
    Args:
        ticker: 6位A股代码
        start_date: 开始日期，YYYY-MM-DD
        end_date: 结束日期，YYYY-MM-DD
    Returns:
        str: 包含新闻数据的格式化文本
    """
    from datetime import datetime
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    look_back_days = max((end_dt - start_dt).days, 7)
    return _get_news(ticker, end_date, look_back_days)


@tool
def get_global_news(
    curr_date: Annotated[str, "当前日期，YYYY-MM-DD"],
    look_back_days: Annotated[Optional[int], "回看天数；省略则使用默认值"] = None,
    limit: Annotated[Optional[int], "返回文章数上限；省略则使用默认值"] = None,
) -> str:
    """
    获取宏观财经新闻数据，数据来源：akshare。
    Args:
        curr_date: 当前日期，YYYY-MM-DD
        look_back_days: 回看天数（暂未使用）
        limit: 返回条数限制（暂未使用）
    Returns:
        str: 包含宏观新闻数据的格式化文本
    """
    return _get_global_news(curr_date, look_back_days, limit)
