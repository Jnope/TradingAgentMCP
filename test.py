import time
from tradingagents.dataflows.interface import get_stock_data, get_technical_indicators, get_fundamentals, get_news

print("Testing A股数据源接口:")
start_time = time.time()
result = get_stock_data("000001", "2025-01-01", "2025-05-30")
end_time = time.time()

print(f"行情数据 - 执行时间: {end_time - start_time:.2f}s, 结果长度: {len(result)} 字符")
print(result[:500])
print("\n---\n")

start_time = time.time()
result = get_fundamentals("000001", "2025-05-30")
end_time = time.time()

print(f"基本面 - 执行时间: {end_time - start_time:.2f}s, 结果长度: {len(result)} 字符")
print(result[:500])
