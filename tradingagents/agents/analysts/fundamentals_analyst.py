import logging

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
    get_money_flow_tool,
    get_language_instruction,
)
from tradingagents.dataflows.config import get_config

logger = logging.getLogger(__name__)


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        ticker = state["company_of_interest"]
        current_date = state["trade_date"]
        logger.info("Fundamentals Analyst started: ticker=%s date=%s", ticker, current_date)
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
            get_money_flow_tool,
        ]

        system_message = (
            "你是一位专业的基本面分析师，负责分析A股公司的基本面信息。请撰写一份全面的基本面分析报告，涵盖公司财务报表、公司概况、基本财务数据和财务历史，以获得公司基本面信息的完整视图，为交易者提供决策参考。请尽可能详细，提供具体、可操作的洞察和支撑证据，帮助交易者做出明智决策。"
            + " 请在报告末尾附上Markdown表格，整理报告中的关键要点，使其条理清晰、易于阅读。"
            + " 可用工具：`get_fundamentals`用于综合公司分析（估值、盈利能力、成长性），`get_balance_sheet`、`get_cashflow`和`get_income_statement`用于具体财务报表，`get_money_flow_tool`用于资金流向数据。"
            + get_language_instruction(),
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
                "Fundamentals Analyst completed: ticker=%s, report length=%d chars",
                ticker, len(report),
            )
        else:
            logger.info(
                "Fundamentals Analyst requesting %d tool calls: %s",
                len(result.tool_calls),
                [tc.get("name", tc.get("function", {}).get("name", "?")) for tc in result.tool_calls],
            )

        return {
            "messages": [result],
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
