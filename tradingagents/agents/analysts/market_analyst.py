import logging

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_indicators,
    get_language_instruction,
    get_stock_data,
)
from tradingagents.dataflows.config import get_config

logger = logging.getLogger(__name__)


def create_market_analyst(llm):

    def market_analyst_node(state):
        ticker = state["company_of_interest"]
        current_date = state["trade_date"]
        logger.info("Market Analyst started: ticker=%s date=%s", ticker, current_date)

        asset_type = state.get("asset_type", "stock")
        instrument_context = build_instrument_context(
            state["company_of_interest"], asset_type
        )

        tools = [
            get_stock_data,
            get_indicators,
        ]

        system_message = (
            """你是一位专业的股票技术分析师，负责分析金融市场行情。你的任务是从以下指标列表中选择**最相关的技术指标**，针对给定的市场状况或交易策略进行分析。目标是选择最多**8个**互补且不冗余的指标。各类别及其指标如下：

均线类：
- close_50_sma: 50日简单移动平均线：中期趋势指标。用途：判断趋势方向，作为动态支撑/阻力位。提示：滞后于价格，需结合更快指标获取及时信号。
- close_200_sma: 200日简单移动平均线：长期趋势基准。用途：确认整体市场趋势，识别金叉/死叉形态。提示：反应较慢，适合战略性趋势确认而非频繁交易入场。
- close_10_ema: 10日指数移动平均线：响应迅速的短期均线。用途：捕捉动量的快速变化和潜在入场点。提示：在震荡市中容易受噪音干扰，需结合更长周期均线过滤假信号。

MACD相关：
- macd: MACD：通过EMA差值计算动量。用途：寻找交叉和背离信号，判断趋势变化。提示：在低波动或横盘市场中需与其他指标确认。
- macds: MACD信号线：MACD线的EMA平滑线。用途：与MACD线交叉触发交易信号。提示：应作为更广泛策略的一部分以避免假阳性。
- macdh: MACD柱状图：显示MACD线与信号线之间的差距。用途：可视化动量强度，及早发现背离。提示：可能波动较大，在快速市场中需配合额外过滤条件。

动量指标：
- rsi: RSI：衡量动量以标记超买/超卖状态。用途：应用70/30阈值，观察背离信号以判断反转。提示：在强趋势中RSI可能持续极端，务必交叉验证趋势分析。

波动率指标：
- boll: 布林带中轨：20日简单移动平均线，作为布林带基准。用途：作为价格运动的动态基准。提示：结合上轨和下轨有效识别突破或反转。
- boll_ub: 布林带上轨：通常为中轨上方2个标准差。用途：标记潜在超买状态和突破区域。提示：需用其他工具确认信号；强趋势中价格可能沿轨道运行。
- boll_lb: 布林带下轨：通常为中轨下方2个标准差。用途：标记潜在超卖状态。提示：需结合额外分析避免假反转信号。
- atr: ATR：平均真实波幅，衡量波动率。用途：根据当前市场波动率设置止损位和调整仓位。提示：属于反应性指标，应作为更广泛风控策略的一部分。

成交量指标：
- vwma: VWMA：以成交量加权的移动平均线。用途：整合价格走势和成交量数据确认趋势。提示：注意成交量异常飙升可能扭曲结果，需与其他成交量分析结合使用。

- 请选择提供多样化且互补信息的指标，避免冗余（例如不要同时选择rsi和stochrsi）。同时简要说明为何这些指标适用于当前市场环境。调用工具时，请使用上述指标的确切名称作为参数，否则调用将失败。请务必先调用get_stock_data获取CSV数据，然后使用get_indicators获取具体指标。请撰写非常详细且深入的趋势分析报告，提供具体、可操作的洞察和支撑证据，帮助交易者做出明智决策。"""
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

        result = chain.invoke({"messages": state["messages"]})

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content
            logger.info(
                "Market Analyst completed: ticker=%s, report length=%d chars",
                ticker, len(report),
            )
        else:
            logger.info(
                "Market Analyst requesting %d tool calls: %s",
                len(result.tool_calls),
                [tc.get("name", tc.get("function", {}).get("name", "?")) for tc in result.tool_calls],
            )

        return {
            "messages": [result],
            "market_report": report,
        }

    return market_analyst_node
