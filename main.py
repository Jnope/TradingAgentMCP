from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()

ta = TradingAgentsGraph(debug=True, config=config)

_, decision = ta.propagate("000001", "2025-05-30")
print(decision)
