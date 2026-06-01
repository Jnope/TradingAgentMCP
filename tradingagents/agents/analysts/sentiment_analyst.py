"""Sentiment analyst — A股社交情绪分析

使用 akshare 获取股吧舆情和个股新闻，注入 prompt 供 LLM 分析。
不再依赖 Reddit/StockTwits（美股社交平台）。
"""

from datetime import datetime, timedelta

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
    get_news,
)
from tradingagents.dataflows.providers.china.akshare_news import (
    get_stock_sentiment,
    get_stock_news,
)


def _seven_days_back(trade_date: str) -> str:
    return (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")


def create_sentiment_analyst(llm):
    """创建 A 股社交情绪分析师节点。

    预获取新闻 + 股吧舆情数据，注入 prompt，LLM 单次调用生成情绪报告。
    """

    def sentiment_analyst_node(state):
        ticker = state["company_of_interest"]
        end_date = state["trade_date"]
        start_date = _seven_days_back(end_date)
        instrument_context = build_instrument_context(ticker)

        news_block = get_news.func(ticker, start_date, end_date)
        sentiment_block = get_stock_sentiment(ticker)

        system_message = _build_system_message(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            news_block=news_block,
            sentiment_block=sentiment_block,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位专业的AI助手，与其他分析师协作。"
                    " 如果你或任何其他分析师得出最终交易建议：**买入/持有/卖出**，"
                    " 请在回复前加上最终交易建议：**买入/持有/卖出**，以便团队知道可以停止。"
                    "\n{system_message}\n"
                    "当前日期：{current_date}。{instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(current_date=end_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm
        result = chain.invoke(state["messages"])

        return {
            "messages": [result],
            "sentiment_report": result.content,
        }

    return sentiment_analyst_node


def _build_system_message(
    *,
    ticker: str,
    start_date: str,
    end_date: str,
    news_block: str,
    sentiment_block: str,
) -> str:
    """组装情绪分析师的系统消息"""
    return f"""你是一位A股市场情绪分析师。你的任务是针对 {ticker} 生成一份涵盖 {start_date} 至 {end_date} 期间的综合情绪分析报告，基于已为你收集的两个互补数据源进行分析。

## 数据来源（已预获取，在下方提供）

### 新闻标题 — 东方财富/新浪财经，过去7天
机构视角。事实驱动，变化较慢的信号。

<start_of_news>
{news_block}
<end_of_news>

### 股吧舆情 — 散户投资者社交平台（东方财富股吧）
快速变化的信号。散户投资者情绪、讨论主题、多空倾向。

<start_of_sentiment>
{sentiment_block}
<end_of_sentiment>

## 分析方法（最佳实践）

1. **阅读舆情数据了解散户投资者情绪。** 关注主导话题、多空倾向和讨论热度。高讨论热度配合明确方向倾向比零散观点信号更强。

2. **寻找跨源分歧。** 如果新闻倾向看空但散户情绪极度看多，这种错配本身就是一个信号——散户可能正倾向于新闻尚未反映的逻辑（反之亦然）。

3. **区分观点与事件。** 新闻标题（"公司发布业绩预告"或"行业政策出台"）是事件；股吧帖子（"这只股票要起飞"或"赶紧跑"）是观点。两者都是输入，但权重应不同。

4. **识别反复出现的叙事主题。** 什么话题在各数据源中反复出现？那就是驱动当前情绪的主导叙事。

5. **诚实面对数据局限。** 如果一个或多个数据源返回的数据有限，请明确标注此注意事项。A股社交数据源相对有限，需注意数据样本的代表性。

6. **识别催化剂和风险**——跨数据源浮现的即将到来的业绩发布、政策变化、竞争威胁、宏观头条等。

7. **历史情绪不具预测性。** 将你的结论定位于供交易者与基本面和技术面综合权衡的信号，而非价格预测。

## 输出要求

请按以下顺序撰写情绪分析报告：

1. **整体情绪方向** — 看多 / 看空 / 中性 / 混合 — 基于数据质量和样本量附上简要的置信度说明。
2. **分数据源拆解** — 新闻和股吧各自传递的信息，附具体证据。
3. **跨源分歧、一致性和关键叙事**。
4. **催化剂和风险**——数据中浮现的催化因素和风险。
5. **Markdown表格**在报告末尾总结关键情绪信号、方向、来源和支撑证据。

{get_language_instruction()}"""


# ---------------------------------------------------------------------------
# Backwards-compatibility shim
# ---------------------------------------------------------------------------
def create_social_media_analyst(llm):
    """Deprecated alias for :func:`create_sentiment_analyst`."""
    import warnings
    warnings.warn(
        "create_social_media_analyst is deprecated and will be removed in a "
        "future version. Use create_sentiment_analyst instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_sentiment_analyst(llm)
