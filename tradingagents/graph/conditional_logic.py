# TradingAgents/graph/conditional_logic.py

import logging

from tradingagents.agents.utils.agent_states import AgentState

logger = logging.getLogger(__name__)


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    def should_continue_market(self, state: AgentState):
        """Determine if market analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            logger.info("Market Analyst → tools_market (%d tool calls)", len(last_message.tool_calls))
            return "tools_market"
        logger.info("Market Analyst → Msg Clear Market (analysis complete)")
        return "Msg Clear Market"

    def should_continue_social(self, state: AgentState):
        """Determine if sentiment-analyst tool round should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            logger.info("Sentiment Analyst → tools_social (%d tool calls)", len(last_message.tool_calls))
            return "tools_social"
        logger.info("Sentiment Analyst → Msg Clear Sentiment (analysis complete)")
        return "Msg Clear Sentiment"

    def should_continue_news(self, state: AgentState):
        """Determine if news analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            logger.info("News Analyst → tools_news (%d tool calls)", len(last_message.tool_calls))
            return "tools_news"
        logger.info("News Analyst → Msg Clear News (analysis complete)")
        return "Msg Clear News"

    def should_continue_fundamentals(self, state: AgentState):
        """Determine if fundamentals analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            logger.info("Fundamentals Analyst → tools_fundamentals (%d tool calls)", len(last_message.tool_calls))
            return "tools_fundamentals"
        logger.info("Fundamentals Analyst → Msg Clear Fundamentals (analysis complete)")
        return "Msg Clear Fundamentals"

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
