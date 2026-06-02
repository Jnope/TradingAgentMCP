# TradingAgents/graph/mini_graph.py

import logging
from typing import Any, Dict

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from tradingagents.agents import (
    create_fundamentals_analyst,
    create_market_analyst,
    create_news_analyst,
    create_sentiment_analyst,
)
from tradingagents.agents.utils.agent_states import AgentState

from .analyst_execution import ANALYST_NODE_SPECS, AnalystNodeSpec

logger = logging.getLogger(__name__)

_ANALYST_FACTORIES = {
    "market": create_market_analyst,
    "fundamentals": create_fundamentals_analyst,
    "news": create_news_analyst,
    "social": create_sentiment_analyst,
}


def _make_should_continue(spec: AnalystNodeSpec):
    def should_continue(state: AgentState) -> str:
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            logger.info(
                "%s → %s (%d tool calls)",
                spec.agent_node, spec.tool_node, len(last_message.tool_calls),
            )
            return spec.tool_node
        logger.info("%s → END (analysis complete)", spec.agent_node)
        return END
    return should_continue


def build_analyst_tool_nodes() -> Dict[str, ToolNode]:
    from tradingagents.agents.utils.core_stock_tools import get_stock_data
    from tradingagents.agents.utils.fundamental_data_tools import (
        get_balance_sheet,
        get_cashflow,
        get_fundamentals,
        get_income_statement,
        get_money_flow_tool,
    )
    from tradingagents.agents.utils.news_data_tools import get_global_news, get_news
    from tradingagents.agents.utils.technical_indicators_tools import get_indicators

    return {
        "market": ToolNode([get_stock_data, get_indicators]),
        "fundamentals": ToolNode([
            get_fundamentals, get_balance_sheet, get_cashflow,
            get_income_statement, get_money_flow_tool,
        ]),
        "news": ToolNode([get_news, get_global_news]),
        "social": ToolNode([get_news]),
    }


def build_single_analyst_graph(
    analyst_type: str,
    llm: Any,
    tool_nodes: Dict[str, ToolNode] | None = None,
) -> StateGraph:
    spec = ANALYST_NODE_SPECS.get(analyst_type)
    if spec is None:
        raise ValueError(f"unknown analyst type: {analyst_type}")

    factory = _ANALYST_FACTORIES.get(analyst_type)
    if factory is None:
        raise ValueError(f"no factory for analyst type: {analyst_type}")

    if tool_nodes is None:
        tool_nodes = build_analyst_tool_nodes()

    node_fn = factory(llm)
    tool_node = tool_nodes[analyst_type]

    workflow = StateGraph(AgentState)

    workflow.add_node(spec.agent_node, node_fn)
    workflow.add_node(spec.tool_node, tool_node)

    workflow.add_edge(START, spec.agent_node)

    workflow.add_conditional_edges(
        spec.agent_node,
        _make_should_continue(spec),
        {spec.tool_node: spec.tool_node, END: END},
    )
    workflow.add_edge(spec.tool_node, spec.agent_node)

    return workflow


def compile_single_analyst_graph(
    analyst_type: str,
    llm: Any,
    tool_nodes: Dict[str, ToolNode] | None = None,
):
    workflow = build_single_analyst_graph(analyst_type, llm, tool_nodes)
    return workflow.compile()
