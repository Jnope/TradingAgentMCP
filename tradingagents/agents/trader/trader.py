"""Trader: turns the Research Manager's investment plan into a concrete transaction proposal."""

from __future__ import annotations

import functools

from langchain_core.messages import AIMessage

from tradingagents.agents.schemas import TraderProposal, render_trader_proposal
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_trader(llm):
    structured_llm = bind_structured(llm, TraderProposal, "Trader")

    def trader_node(state, name):
        company_name = state["company_of_interest"]
        asset_type = state.get("asset_type", "stock")
        instrument_context = build_instrument_context(company_name, asset_type)
        investment_plan = state["investment_plan"]

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一位专业交易员，负责分析市场数据并做出投资决策。"
                    "基于你的分析，提供具体的买入、卖出或持有建议。"
                    "你的推理应以分析师报告和研究计划为依据。"
                    + get_language_instruction()
                ),
            },
            {
                "role": "user",
                "content": (
                    f"基于分析师团队的全面分析，以下是为 {company_name} 定制的投资计划。"
                    f"{instrument_context} 该计划综合了当前技术面市场趋势、宏观经济指标和"
                    f"社交媒体情绪的洞察。请以此计划为基础评估你的下一个交易决策。\n\n"
                    f"投资计划：{investment_plan}\n\n"
                    f"请利用这些洞察做出明智且战略性的决策。"
                ),
            },
        ]

        trader_plan = invoke_structured_or_freetext(
            structured_llm,
            llm,
            messages,
            render_trader_proposal,
            "Trader",
        )

        return {
            "messages": [AIMessage(content=trader_plan)],
            "trader_investment_plan": trader_plan,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
