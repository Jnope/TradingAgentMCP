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

from langchain_core.messages import HumanMessage
from transwarp.timelyre import DatabaseConn

from tradingagents_mcp.validators import _summarize_text

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
        build_response,
        extract_full_result,
        extract_detail_result,
    )
    from tradingagents_mcp.shared_context import get_shared_ctx

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

    ctx_ = get_shared_ctx()
    result = build_response(
        tool="trading_agent",
        success=True,
        symbol=symbol,
        market=market,
        trade_date=trade_date,
        analysts_used=analysts,
        elapsed_seconds=elapsed,
        data=extract_full_result(state, llm=ctx_.quick_thinking_llm),
    )

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


def test_market_analyst(symbol="688031", trade_date="2026-05-20"):
    from tradingagents_mcp.validators import validate_symbol, normalize_date, nearest_trade_date, build_config
    from tradingagents_mcp.shared_context import get_shared_ctx
    from tradingagents.graph.mini_graph import compile_single_analyst_graph

    symbol, market = validate_symbol(symbol)
    trade_date = nearest_trade_date(normalize_date(trade_date))
    print(f"📊 技术面分析: {symbol}({market}) @ {trade_date}")

    config = build_config()
    print(f"🤖 LLM: {config.get('llm_provider')} / {config.get('quick_think_llm')}")

    ctx_ = get_shared_ctx()
    graph = compile_single_analyst_graph("market", ctx_.quick_thinking_llm)

    state = {
        "messages": [HumanMessage(content=f"请分析股票 {symbol}")],
        "company_of_interest": symbol,
        "trade_date": trade_date,
        "asset_type": "stock",
    }

    t0 = time.time()
    result_state = graph.invoke(state)
    elapsed = round(time.time() - t0, 1)

    report = result_state.get("market_report", "")

    print(f"\n{'='*60}")
    print(f"✅ 技术面分析完成，耗时 {elapsed}s，报告 {len(report)} 字符")
    print(f"{'='*60}")
    if report:
        print(f"\n{report}")
    else:
        print("\n⚠️ market_report 为空！")
        print(f"state keys: {list(result_state.keys())}")
        for msg in result_state.get("messages", []):
            print(f"  message: {type(msg).__name__}, content_len={len(msg.content) if hasattr(msg, 'content') else 'N/A'}, tool_calls={getattr(msg, 'tool_calls', None)}")

    t1 = time.time()
    simple_report = _summarize_text(ctx_.quick_thinking_llm, report, "市场技术分析报告" )
    elapsed1 = round(time.time() - t1, 1)

    print(f"\n{'='*60}")
    print(f"✅ 技术面分析总结完成，耗时 {elapsed1}s，报告 {len(simple_report)} 字符")
    print(f"{'='*60}")
    if simple_report:
        print(f"\n{simple_report}")
    else:
        print("\n⚠️ simple_report 为空！")

    return report


def test_timelyre():
    try:
        jdbc_http_proxy = os.environ.get("JDBC_HTTP_PROXY", "172.18.192.74:9998")
        real_conn = os.environ.get(
            "TM_REAL_CONN", "jdbc:hive2://172.18.192.75:10006"
        )
        db_name = os.environ.get("TM_DB_NAME", "meta_data")
        db_user = os.environ.get("TM_DB_USER", "admin")
        password = os.environ.get("TM_DB_PASSWORD", "admin")
        token = os.environ.get("GUARDIAN_TOKEN", "UgJRRGe7qMAKcirOQ017-TDH")
        _db_conn = DatabaseConn(
            jdbc_http_proxy=jdbc_http_proxy,
            real_conn=real_conn,
            db=db_name,
            auth_type="ldap",
            username=db_user,
            password=password,
            token=token,
            disable_cancel=True,
            session_timeout=60000,
            login_timeout=15000,
        )
        print("TransMatrix DatabaseConn 初始化成功")
        import pandas as pd

        result: pd.DataFrame = _db_conn.query_as_df("sw_industry", query="""SELECT a.*
FROM `sw_industry` a
WHERE NOT EXISTS (
    SELECT 1
    FROM `sw_industry` b
    WHERE b.code = a.code 
      AND b.datetime > a.datetime
)""")
        result.to_csv('industry.csv', index=False, encoding='utf-8-sig')
        # result: pd.DataFrame = _db_conn.query_as_df("stock_bar_1day", query=f"SELECT `trade_day`, `open`, `high`, `low`, `close`, `volume`, `turnover`, `vwap`, `factor` "
        # f"FROM `stock_bar_1day` "
        # f"WHERE `code` = '688031.SH' AND `datetime` >= '2026-01-01 00:00:00' AND `datetime` < '2026-05-21 00:00:00' ", combine_ignore_index=True)
        print(len(result))
    except Exception as e:
        print(f"DatabaseConn初始化失败: {e}")
        pass


if __name__ == "__main__":
    _load_env_from_opencode_json()
    # test_market_analyst()
    test_timelyre()
