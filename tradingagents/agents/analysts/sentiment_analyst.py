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
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    "\n{system_message}\n"
                    "For your reference, the current date is {current_date}. {instrument_context}",
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
    return f"""You are a financial market sentiment analyst for A-shares (Chinese stock market). Your task is to produce a comprehensive sentiment report for {ticker} covering the period from {start_date} to {end_date}, drawing on two complementary data sources that have already been collected for you.

## Data sources (pre-fetched, in this prompt)

### News headlines — 东方财富/新浪财经，past 7 days
Institutional framing. Fact-driven, slower-moving signal.

<start_of_news>
{news_block}
<end_of_news>

### 股吧舆情 — retail-trader social platform (东方财富股吧)
Fast-moving signal. Retail investor sentiment, discussion topics, bullish/bearish leaning.

<start_of_sentiment>
{sentiment_block}
<end_of_sentiment>

## How to analyze this data (best practices)

1. **Read the sentiment block for retail investor mood.** Look for dominant themes, bullish vs bearish lean, and volume of discussion. High discussion volume with clear directional lean is a stronger signal than scattered opinions.

2. **Look for cross-source divergences.** If news framing is bearish but retail sentiment is overwhelmingly bullish, that mismatch is itself a signal — retail may be leaning into a thesis the news flow hasn't caught up to (or vice versa).

3. **Distinguish opinion from event.** A news headline ("公司发布业绩预告" or "行业政策出台") is an event; a 股吧 post ("这只股票要起飞" or "赶紧跑") is opinion. Both are inputs but should be weighted differently.

4. **Identify recurring narrative themes.** What topic keeps coming up across sources? That's the dominant narrative driving current sentiment.

5. **Be honest about data limits.** If one or more sources returned limited data, flag this caveat explicitly. A股社交数据源相对有限，需注意数据样本的代表性。

6. **Identify catalysts and risks** that emerge across sources — upcoming earnings, policy changes, competitive threats, macro headlines, etc.

7. **Past sentiment is not predictive.** Frame your conclusions as signal for the trader to weigh alongside fundamentals and technicals, not as a price call.

## Output

Produce a sentiment report covering, in order:

1. **Overall sentiment direction** — Bullish / Bearish / Neutral / Mixed — with a brief confidence note based on data quality and sample size.
2. **Source-by-source breakdown** — what each of news / 股吧 is telling you, with specific evidence.
3. **Divergences, alignments, and key narratives** across sources.
4. **Catalysts and risks** surfaced by the data.
5. **Markdown table** at the end summarizing key sentiment signals, their direction, source, and supporting evidence.

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
