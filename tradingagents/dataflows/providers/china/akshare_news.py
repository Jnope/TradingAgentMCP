"""
akshare 新闻/舆情数据获取

使用 akshare 获取 A 股个股新闻、社交舆情和宏观财经新闻。
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def get_stock_news(symbol: str, look_back_days: int = 7) -> str:
    """获取个股新闻（东方财富/新浪财经）

    Args:
        symbol: 6位A股代码，如 000001
        look_back_days: 回看天数，默认7天

    Returns:
        格式化的新闻文本
    """
    try:
        import akshare as ak
    except ImportError:
        return f"akshare 未安装，无法获取 {symbol} 新闻数据"

    try:
        from .internal_code_mapper import to_tm_code
        tm_code = to_tm_code(symbol)
        stock_code = tm_code.split(".")[0] if "." in tm_code else symbol

        end_date = datetime.now()
        start_date = end_date - timedelta(days=look_back_days)

        df = ak.stock_news_em(symbol=stock_code)

        if df is None or df.empty:
            return f"{symbol} 近 {look_back_days} 天无新闻数据"

        lines = [f"# {symbol} 个股新闻 (近{look_back_days}天)\n"]
        lines.append(f"# 数据获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        count = 0
        for _, row in df.iterrows():
            if count >= 20:
                break
            title = row.get("新闻标题", row.get("title", ""))
            content = row.get("新闻内容", row.get("content", ""))
            source = row.get("文章来源", row.get("source", ""))
            pub_time = row.get("发布时间", row.get("datetime", ""))

            if title:
                lines.append(f"### {title}")
                if source:
                    lines.append(f"来源: {source}")
                if pub_time:
                    lines.append(f"时间: {pub_time}")
                if content:
                    lines.append(f"{content[:500]}")
                lines.append("")
                count += 1

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"akshare 获取 {symbol} 新闻失败: {e}")
        return f"获取 {symbol} 新闻数据失败: {e}"


def get_stock_sentiment(symbol: str) -> str:
    """获取社交舆情（股吧）

    Args:
        symbol: 6位A股代码，如 000001

    Returns:
        格式化的舆情文本
    """
    try:
        import akshare as ak
    except ImportError:
        return f"akshare 未安装，无法获取 {symbol} 舆情数据"

    try:
        from .internal_code_mapper import to_tm_code
        tm_code = to_tm_code(symbol)
        stock_code = tm_code.split(".")[0] if "." in tm_code else symbol

        try:
            df = ak.stock_guba_sina(symbol=stock_code)
            if df is not None and not df.empty:
                lines = [f"# {symbol} 股吧舆情\n"]
                lines.append(f"# 数据获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                count = 0
                for _, row in df.iterrows():
                    if count >= 15:
                        break
                    title = row.get("title", row.get("主题", ""))
                    content = row.get("content", row.get("内容", ""))
                    author = row.get("author", row.get("作者", ""))

                    if title:
                        lines.append(f"- {title}")
                        if content:
                            lines.append(f"  {content[:300]}")
                        lines.append("")
                        count += 1
                return "\n".join(lines)
        except Exception as e:
            logger.debug(f"新浪股吧数据获取失败: {e}")

        return f"{symbol} 暂无社交舆情数据"

    except Exception as e:
        logger.warning(f"akshare 获取 {symbol} 舆情失败: {e}")
        return f"获取 {symbol} 舆情数据失败: {e}"


def get_macro_news() -> str:
    """获取宏观财经新闻

    Returns:
        格式化的宏观新闻文本
    """
    try:
        import akshare as ak
    except ImportError:
        return "akshare 未安装，无法获取宏观新闻"

    try:
        df = ak.news_cctv(date=datetime.now().strftime("%Y%m%d"))

        if df is None or df.empty:
            return "暂无宏观财经新闻数据"

        lines = ["# 宏观财经新闻\n"]
        lines.append(f"# 数据获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        count = 0
        for _, row in df.iterrows():
            if count >= 15:
                break
            title = row.get("title", "")
            content = row.get("content", "")
            if title:
                lines.append(f"### {title}")
                if content:
                    lines.append(f"{content[:500]}")
                lines.append("")
                count += 1

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"akshare 获取宏观新闻失败: {e}")
        try:
            import akshare as ak
            df = ak.news_economic_baidu(symbol="宏观经济")
            if df is not None and not df.empty:
                lines = ["# 宏观财经新闻\n"]
                count = 0
                for _, row in df.iterrows():
                    if count >= 15:
                        break
                    title = row.get("title", "")
                    content = row.get("content", row.get("abstract", ""))
                    if title:
                        lines.append(f"### {title}")
                        if content:
                            lines.append(f"{content[:500]}")
                        lines.append("")
                        count += 1
                return "\n".join(lines)
        except Exception:
            pass
        return f"获取宏观新闻失败: {e}"
