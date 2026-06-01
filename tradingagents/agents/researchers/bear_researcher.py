from tradingagents.agents.utils.agent_utils import get_language_instruction


def create_bear_researcher(llm):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        asset_type = state.get("asset_type", "stock")
        target_label = "股票" if asset_type == "stock" else "资产"
        fundamentals_label = (
            "公司基本面报告"
            if asset_type == "stock"
            else "资产基本面报告（加密货币可能不可用）"
        )

        prompt = f"""你是一位看跌分析师，负责论证不投资该{target_label}的理由。你的目标是提出基于充分推理的论证，强调风险、挑战和负面指标。利用提供的研究和数据来突出潜在的不利因素并有效反驳看涨论点。

请重点关注以下方面：

- 风险和挑战：突出市场饱和、财务不稳定或宏观经济威胁等可能阻碍股票表现的因素。
- 竞争劣势：强调市场地位较弱、创新下降或来自竞争对手威胁等脆弱性。
- 负面指标：使用财务数据、市场趋势或最近不利消息的证据来支持你的立场。
- 反驳看涨观点：用具体数据和合理推理批判性分析看涨论点，揭露弱点或过度乐观的假设。
- 参与讨论：以对话风格呈现你的论点，直接回应看涨分析师的观点并进行有效辩论，而不仅仅是列举事实。

可用资源：

市场研究报告：{market_research_report}
社交媒体情绪报告：{sentiment_report}
最新世界事务新闻：{news_report}
{fundamentals_label}：{fundamentals_report}
辩论对话历史：{history}
最后的看涨论点：{current_response}
请使用这些信息提供令人信服的看跌论点，反驳看涨声明，并参与动态辩论，展示投资该{target_label}的风险和弱点。
""" + get_language_instruction()

        response = llm.invoke(prompt)

        argument = f"看跌分析师: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bear_node
