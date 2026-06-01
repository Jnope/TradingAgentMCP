"""Research Manager: turns the bull/bear debate into a structured investment plan for the trader."""

from __future__ import annotations

from tradingagents.agents.schemas import ResearchPlan, render_research_plan
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_research_manager(llm):
    structured_llm = bind_structured(llm, ResearchPlan, "Research Manager")

    def research_manager_node(state) -> dict:
        instrument_context = build_instrument_context(state["company_of_interest"])
        history = state["investment_debate_state"].get("history", "")

        investment_debate_state = state["investment_debate_state"]

        prompt = f"""作为研究主管和辩论主持人，你的职责是批判性地评估本轮辩论，并为交易员提供明确、可执行的投资计划。

{instrument_context}

---

**评级标准**（请使用以下其中之一）：
- **买入**：对看涨逻辑有强烈信心；建议建仓或加仓
- **增持**：偏乐观；建议逐步增加敞口
- **持有**：观点均衡；建议维持当前仓位
- **减持**：偏谨慎；建议减少敞口
- **卖出**：对看跌逻辑有强烈信心；建议清仓或回避

当辩论中最强有力的论据支持某一立场时，请做出明确承诺；仅在双方证据确实均衡时才使用"持有"评级。

---

**辩论历史：**
{history}""" + get_language_instruction()

        investment_plan = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_research_plan,
            "Research Manager",
        )

        new_investment_debate_state = {
            "judge_decision": investment_plan,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": investment_plan,
            "count": investment_debate_state["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": investment_plan,
        }

    return research_manager_node
