"""
PyCharm debug 测试脚本

模拟 trading_agent 全流程，设置 .opencode.json 中的环境变量后直接调用内部逻辑。
支持断点调试每个环节。

用法:
    1. PyCharm 中打开此文件
    2. 在需要调试的行设置断点
    3. 右键 → Debug
"""

import os
import json
import logging
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _load_env_from_opencode_json():
    project_root = Path(__file__).parent
    config_path = project_root / ".opencode.json"
    if not config_path.exists():
        print(f"⚠ .opencode.json not found: {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    env = config.get("mcp", {}).get("tradingagents", {}).get("environment", {})
    for key, value in env.items():
        os.environ.setdefault(key, str(value))
    os.environ.pop('HTTP_PROXY', None)
    os.environ.pop('HTTPS_PROXY', None)
    os.environ.pop('http_proxy', None)
    os.environ.pop('https_proxy', None)
    os.environ.setdefault('NO_PROXY', "*")

    print(f"✅ Loaded {len(env)} env vars from .opencode.json")


def test_trading_agent():
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents_mcp.validators import (
        validate_symbol,
        normalize_date,
        nearest_trade_date,
        build_config,
        extract_full_result,
    )

    symbol = "688031"
    trade_date = "2026-05-20"

    symbol, market = validate_symbol(symbol)
    trade_date = nearest_trade_date(normalize_date(trade_date))
    print(f"📊 分析目标: {symbol}({market}) @ {trade_date}")

    config = build_config()
    config["max_debate_rounds"] = 1
    config["max_risk_discuss_rounds"] = 1
    print(f"🤖 LLM: {config.get('llm_provider')} / {config.get('deep_think_llm')} / {config.get('quick_think_llm')}")

    analysts = ["market", "social", "news", "fundamentals"]
    print(f"👥 分析师: {analysts}")
    print("🚀 开始全流程分析...\n")

    ta = TradingAgentsGraph(selected_analysts=analysts, debug=False, config=config)

    t0 = time.time()
    state = ta.propagate(symbol, trade_date)
    elapsed = round(time.time() - t0, 1)

    result = {
        "success": True,
        "symbol": symbol,
        "market": market,
        "trade_date": trade_date,
        "analysts_used": analysts,
        "elapsed_seconds": elapsed,
        **extract_full_result(state),
    }

    print(f"\n{'='*60}")
    print(f"✅ 分析完成，耗时 {elapsed}s")
    print(f"{'='*60}")

    for key, value in result.items():
        if isinstance(value, str) and len(value) > 200:
            print(f"\n📝 {key} ({len(value)} 字符):")
            print(value[:200] + "...")
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, str) and len(sub_value) > 200:
                    print(f"\n📝 {key}.{sub_key} ({len(sub_value)} 字符):")
                    print(sub_value[:200] + "...")
                else:
                    print(f"\n📝 {key}.{sub_key}: {sub_value}")
        else:
            print(f"\n📝 {key}: {value}")

    return result


if __name__ == "__main__":
    _load_env_from_opencode_json()
    result = test_trading_agent()
