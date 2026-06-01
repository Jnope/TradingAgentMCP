from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP):

    @mcp.prompt(title="股票分析")
    def stock_analysis_prompt(symbol: str, trade_date: str) -> str:
        return (
            f"请对A股 {symbol} 进行全面分析，交易日为 {trade_date}。\n"
            "使用 trading_agent 工具执行完整分析流程。\n"
            "全流程需要3-10分钟，分析完成后基于返回的报告和决策给出综合解读。"
        )

    @mcp.prompt(title="技术面分析")
    def technical_analysis_prompt(symbol: str, trade_date: str) -> str:
        return (
            f"请分析A股 {symbol} 的技术面，交易日 {trade_date}。\n"
            "使用 market_analyst 工具获取技术分析报告，大约需要30秒。"
        )

    @mcp.prompt(title="基本面分析")
    def fundamentals_prompt(symbol: str, trade_date: str) -> str:
        return (
            f"请分析A股 {symbol} 的基本面，交易日 {trade_date}。\n"
            "使用 fundamentals_analyst 工具获取估值和财务分析报告。"
        )

    @mcp.prompt(title="新闻分析")
    def news_prompt(symbol: str, trade_date: str) -> str:
        return (
            f"请分析A股 {symbol} 的近期新闻，交易日 {trade_date}。\n"
            "使用 news_analyst 工具获取新闻分析报告。"
        )

    @mcp.prompt(title="情绪分析")
    def sentiment_prompt(symbol: str, trade_date: str) -> str:
        return (
            f"请分析A股 {symbol} 的社交情绪，交易日 {trade_date}。\n"
            "使用 social_analyst 工具获取投资者情绪报告。"
        )
