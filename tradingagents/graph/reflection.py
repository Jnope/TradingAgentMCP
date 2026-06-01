# TradingAgents/graph/reflection.py

from typing import Any


class Reflector:
    """Handles reflection on trading decisions."""

    def __init__(self, quick_thinking_llm: Any):
        """Initialize the reflector with an LLM."""
        self.quick_thinking_llm = quick_thinking_llm
        self.log_reflection_prompt = self._get_log_reflection_prompt()

    def _get_log_reflection_prompt(self) -> str:
        """Concise prompt for reflect_on_final_decision (Phase B log entries).

        Produces 2-4 sentences of plain prose — compact enough to be re-injected
        into future agent prompts without bloating the context window.
        """
        return (
            "你是一位交易分析师，正在回顾自己过去的决策（现在结果已知）。\n"
            "请撰写2-4句纯文本（不含项目符号、标题或Markdown格式）。\n\n"
            "按顺序覆盖以下要点：\n"
            "1. 方向性判断是否正确？（引用alpha数据）\n"
            "2. 投资逻辑中哪部分成立或失效？\n"
            "3. 一条可应用于下一次类似分析的具体教训。\n\n"
            "请具体且简洁。你的输出将逐字存储在决策日志中，"
            "并被未来的分析师重新阅读，因此每个字都应有其价值。"
        )

    def reflect_on_final_decision(
        self,
        final_decision: str,
        raw_return: float,
        alpha_return: float,
        benchmark_name: str = "SPY",
    ) -> str:
        """Single reflection call on the final trade decision with outcome context.

        Used by Phase B deferred reflection. The final_trade_decision already
        synthesises all analyst insights, so no separate market context is needed.
        ``benchmark_name`` is the label used for the alpha line (e.g. ``"SPY"``
        for US tickers, ``"^N225"`` for ``.T`` listings); defaults to SPY for
        callers that haven't been updated to thread the benchmark through.
        """
        messages = [
            ("system", self.log_reflection_prompt),
            (
                "human",
                (
                    f"绝对收益: {raw_return:+.1%}\n"
                    f"相对{benchmark_name}的超额收益: {alpha_return:+.1%}\n\n"
                    f"最终决策:\n{final_decision}"
                ),
            ),
        ]
        return self.quick_thinking_llm.invoke(messages).content
