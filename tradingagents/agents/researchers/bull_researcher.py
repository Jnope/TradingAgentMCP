from tradingagents.agents.utils.agent_utils import get_language_instruction


def create_bull_researcher(llm):
    def bull_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")

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

        prompt = f"""你是一位看涨分析师，负责为投资该{target_label}构建强有力的论证。你的任务是建立基于证据的强有力案例，强调增长潜力、竞争优势和积极的市场指标。利用提供的研究和数据来解决担忧并有效反驳看跌论点。

请重点关注以下方面：
- 增长潜力：突出公司的市场机会、收入预期和可扩展性。
- 竞争优势：强调独特产品、强势品牌或主导市场地位等因素。
- 积极指标：使用财务健康状况、行业趋势和最新积极消息作为证据。
- 反驳看跌观点：用具体数据和合理推理批判性分析看跌论点，全面解决担忧并说明为什么看涨观点更有说服力。
- 参与讨论：以对话风格呈现你的论点，直接回应看跌分析师的观点并进行有效辩论，而不仅仅是列举数据。

可用资源：
市场研究报告：{market_research_report}
社交媒体情绪报告：{sentiment_report}
最新世界事务新闻：{news_report}
{fundamentals_label}：{fundamentals_report}
辩论对话历史：{history}
最后的看跌论点：{current_response}
请使用这些信息提供令人信服的看涨论点，反驳看跌担忧，并参与动态辩论，展示看涨立场的优势。
""" + get_language_instruction()

        response = llm.invoke(prompt)

        argument = f"看涨分析师: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bull_history": bull_history + "\n" + argument,
            "bear_history": investment_debate_state.get("bear_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bull_node
