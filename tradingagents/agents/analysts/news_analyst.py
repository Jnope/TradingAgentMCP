import logging

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_global_news,
    get_language_instruction,
    get_news,
)
from tradingagents.dataflows.config import get_config

logger = logging.getLogger(__name__)


def create_news_analyst(llm):
    def news_analyst_node(state):
        ticker = state["company_of_interest"]
        current_date = state["trade_date"]
        logger.info("News Analyst started: ticker=%s date=%s", ticker, current_date)
        asset_type = state.get("asset_type", "stock")
        asset_label = "公司" if asset_type == "stock" else "资产"
        instrument_context = build_instrument_context(
            state["company_of_interest"], asset_type
        )

        tools = [
            get_news,
            get_global_news,
        ]

        system_message = (
            f"你是一位专业的财经新闻分析师，负责分析近期新闻和市场趋势。请撰写一份与交易和宏观经济相关的综合新闻分析报告。可用工具：get_news(query, start_date, end_date)用于{asset_label}特定或有针对性的新闻搜索，get_global_news(curr_date, look_back_days, limit)用于更广泛的宏观经济新闻。请提供具体、可操作的洞察和支撑证据，帮助交易者做出明智决策。"
            + """ 请在报告末尾附上Markdown表格，整理报告中的关键要点，使其条理清晰、易于阅读。"""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位专业的AI助手，与其他分析师协作。"
                    " 使用提供的工具推进分析任务。"
                    " 如果你无法完全回答也没关系，具有不同工具的其他分析师"
                    " 会在你停下的地方继续。请尽可能推进分析。"
                    " 如果你或任何其他分析师得出最终交易建议：**买入/持有/卖出**，"
                    " 请在回复前加上最终交易建议：**买入/持有/卖出**，以便团队知道可以停止。"
                    " 你可以使用以下工具：{tool_names}。\n{system_message}"
                    "当前日期：{current_date}。{instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content
            logger.info(
                "News Analyst completed: ticker=%s, report length=%d chars",
                ticker, len(report),
            )
        else:
            logger.info(
                "News Analyst requesting %d tool calls: %s",
                len(result.tool_calls),
                [tc.get("name", tc.get("function", {}).get("name", "?")) for tc in result.tool_calls],
            )

        return {
            "messages": [result],
            "news_report": report,
        }

    return news_analyst_node
