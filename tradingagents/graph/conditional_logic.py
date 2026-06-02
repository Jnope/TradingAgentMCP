# TradingAgents/graph/conditional_logic.py

import logging

from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.graph.analyst_execution import ANALYST_NODE_SPECS, AnalystNodeSpec

logger = logging.getLogger(__name__)


def make_should_continue(spec: AnalystNodeSpec):
    """Factory: 为一个分析师生成条件边函数（完整图用，路由到 clear_node）。"""
    def should_continue(state: AgentState) -> str:
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            logger.info(
                "%s → %s (%d tool calls)",
                spec.agent_node, spec.tool_node, len(last_message.tool_calls),
            )
            return spec.tool_node
        logger.info("%s → %s (analysis complete)", spec.agent_node, spec.clear_node)
        return spec.clear_node
    return should_continue


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

        for key, spec in ANALYST_NODE_SPECS.items():
            setattr(self, f"should_continue_{key}", make_should_continue(spec))

    def should_continue_debate(self, state: AgentState) -> str:
        """Determine if debate should continue."""
        count = state["investment_debate_state"]["count"]
        max_count = 2 * self.max_debate_rounds

        if count >= max_count:
            logger.info(
                "Debate round %d/%d reached max → Research Manager",
                count, max_count,
            )
            return "Research Manager"
        if state["investment_debate_state"]["current_response"].startswith("看涨"):
            logger.info("Debate round %d/%d, last=看涨 → Bear Researcher", count, max_count)
            return "Bear Researcher"
        logger.info("Debate round %d/%d, last=看跌 → Bull Researcher", count, max_count)
        return "Bull Researcher"

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determine if risk analysis should continue."""
        count = state["risk_debate_state"]["count"]
        max_count = 3 * self.max_risk_discuss_rounds

        if count >= max_count:
            logger.info(
                "Risk debate round %d/%d reached max → Portfolio Manager",
                count, max_count,
            )
            return "Portfolio Manager"
        speaker = state["risk_debate_state"]["latest_speaker"]
        if speaker.startswith("激进"):
            next_node = "Conservative Analyst"
        elif speaker.startswith("保守"):
            next_node = "Neutral Analyst"
        else:
            next_node = "Aggressive Analyst"
        logger.info(
            "Risk debate round %d/%d, last_speaker=%s → %s",
            count, max_count, speaker, next_node,
        )
        return next_node
