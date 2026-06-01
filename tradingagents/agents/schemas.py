"""Pydantic schemas used by agents that produce structured output.

The framework's primary artifact is still prose: each agent's natural-language
reasoning is what users read in the saved markdown reports and what the
downstream agents read as context.  Structured output is layered onto the
three decision-making agents (Research Manager, Trader, Portfolio Manager)
so that:

- Their outputs follow consistent section headers across runs and providers
- Each provider's native structured-output mode is used (json_schema for
  OpenAI/xAI, response_schema for Gemini, tool-use for Anthropic)
- Schema field descriptions become the model's output instructions, freeing
  the prompt body to focus on context and the rating-scale guidance
- A render helper turns the parsed Pydantic instance back into the same
  markdown shape the rest of the system already consumes, so display,
  memory log, and saved reports keep working unchanged
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared rating types
# ---------------------------------------------------------------------------


class PortfolioRating(str, Enum):
    """5-tier rating used by the Research Manager and Portfolio Manager."""

    BUY = "买入"
    OVERWEIGHT = "增持"
    HOLD = "持有"
    UNDERWEIGHT = "减持"
    SELL = "卖出"


class TraderAction(str, Enum):
    """3-tier transaction direction used by the Trader.

    The Trader's job is to translate the Research Manager's investment plan
    into a concrete transaction proposal: should the desk execute a Buy, a
    Sell, or sit on Hold this round.  Position sizing and the nuanced
    Overweight / Underweight calls happen later at the Portfolio Manager.
    """

    BUY = "买入"
    HOLD = "持有"
    SELL = "卖出"


# ---------------------------------------------------------------------------
# Research Manager
# ---------------------------------------------------------------------------


class ResearchPlan(BaseModel):
    """Structured investment plan produced by the Research Manager.

    Hand-off to the Trader: the recommendation pins the directional view,
    the rationale captures which side of the bull/bear debate carried the
    argument, and the strategic actions translate that into concrete
    instructions the trader can execute against.
    """

    recommendation: PortfolioRating = Field(
        description=(
            "投资建议。从买入/增持/持有/减持/卖出中精确选择一个。"
            "仅在双方证据确实均衡时使用\"持有\"；否则应倾向于论据更强的一方。"
        ),
    )
    rationale: str = Field(
        description=(
            "用对话方式总结辩论双方的关键观点，最后说明哪些论点导致了该建议。"
            "像对队友说话一样自然表达。"
        ),
    )
    strategic_actions: str = Field(
        description=(
            "交易员执行该建议的具体步骤，"
            "包括与评级一致的仓位管理指导。"
        ),
    )


def render_research_plan(plan: ResearchPlan) -> str:
    """Render a ResearchPlan to markdown for storage and the trader's prompt context."""
    return "\n".join([
        f"**投资建议**: {plan.recommendation.value}",
        "",
        f"**理由**: {plan.rationale}",
        "",
        f"**战略行动**: {plan.strategic_actions}",
    ])


# ---------------------------------------------------------------------------
# Trader
# ---------------------------------------------------------------------------


class TraderProposal(BaseModel):
    """Structured transaction proposal produced by the Trader.

    The trader reads the Research Manager's investment plan and the analyst
    reports, then turns them into a concrete transaction: what action to
    take, the reasoning that justifies it, and the practical levels for
    entry, stop-loss, and sizing.
    """

    action: TraderAction = Field(
        description="交易方向。从买入/持有/卖出中精确选择一个。",
    )
    reasoning: str = Field(
        description=(
            "支持该操作的理由，以分析师报告和研究计划为依据。"
            "两到四句话。"
        ),
    )
    entry_price: Optional[float] = Field(
        default=None,
        description="可选的入场目标价格，以标的计价货币表示。",
    )
    stop_loss: Optional[float] = Field(
        default=None,
        description="可选的止损价格，以标的计价货币表示。",
    )
    position_sizing: Optional[str] = Field(
        default=None,
        description="可选的仓位管理指导，例如'组合的5%'。",
    )


def render_trader_proposal(proposal: TraderProposal) -> str:
    """Render a TraderProposal to markdown.

    The trailing ``最终交易建议: **买入/持有/卖出**`` line is
    preserved for backward compatibility with the analyst stop-signal text
    and any external code that greps for it.
    """
    parts = [
        f"**操作**: {proposal.action.value}",
        "",
        f"**理由**: {proposal.reasoning}",
    ]
    if proposal.entry_price is not None:
        parts.extend(["", f"**入场价格**: {proposal.entry_price}"])
    if proposal.stop_loss is not None:
        parts.extend(["", f"**止损价**: {proposal.stop_loss}"])
    if proposal.position_sizing:
        parts.extend(["", f"**仓位管理**: {proposal.position_sizing}"])
    parts.extend([
        "",
        f"最终交易建议: **{proposal.action.value.upper()}**",
    ])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Portfolio Manager
# ---------------------------------------------------------------------------


class PortfolioDecision(BaseModel):
    """Structured output produced by the Portfolio Manager.

    The model fills every field as part of its primary LLM call; no separate
    extraction pass is required. Field descriptions double as the model's
    output instructions, so the prompt body only needs to convey context and
    the rating-scale guidance.
    """

    rating: PortfolioRating = Field(
        description=(
            "最终仓位评级。从买入/增持/持有/减持/卖出中精确选择一个，"
            "基于分析师辩论做出决定。"
        ),
    )
    executive_summary: str = Field(
        description=(
            "简明的行动计划，涵盖入场策略、仓位管理、"
            "关键风险水平和时间周期。两到四句话。"
        ),
    )
    investment_thesis: str = Field(
        description=(
            "以分析师辩论中的具体证据为依据的详细推理。"
            "如果提示上下文中引用了过往经验教训，请纳入；"
            "否则仅依赖当前分析。"
        ),
    )
    price_target: Optional[float] = Field(
        default=None,
        description="可选的目标价格，以标的计价货币表示。",
    )
    time_horizon: Optional[str] = Field(
        default=None,
        description="可选的建议持有期，例如'3-6个月'。",
    )


def render_pm_decision(decision: PortfolioDecision) -> str:
    """Render a PortfolioDecision back to the markdown shape the rest of the system expects.

    Memory log, CLI display, and saved report files all read this markdown,
    so the rendered output preserves the exact section headers (``**Rating**``,
    ``**Executive Summary**``, ``**Investment Thesis**``) that downstream
    parsers and the report writers already handle.
    """
    parts = [
        f"**评级**: {decision.rating.value}",
        "",
        f"**执行摘要**: {decision.executive_summary}",
        "",
        f"**投资逻辑**: {decision.investment_thesis}",
    ]
    if decision.price_target is not None:
        parts.extend(["", f"**目标价格**: {decision.price_target}"])
    if decision.time_horizon:
        parts.extend(["", f"**时间周期**: {decision.time_horizon}"])
    return "\n".join(parts)
