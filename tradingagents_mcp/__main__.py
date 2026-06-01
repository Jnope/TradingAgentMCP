"""
TradingAgents A股 MCP Server 入口

启动方式:
  stdio:    python -m tradingagents_mcp
  http:     MCP_TRANSPORT=streamable-http python -m tradingagents_mcp
  check:    python -m tradingagents_mcp check
"""

import os
import sys
import logging
from pathlib import Path


def _setup_logging():
    from logging.handlers import TimedRotatingFileHandler

    level_str = os.getenv("TRADINGAGENTS_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_str, logging.WARNING)
    log_dir = os.getenv(
        "TRADINGAGENTS_LOG_DIR",
        str(Path.home() / ".tradingagents" / "logs"),
    )
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    fmt_console = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    fmt_file = "%(asctime)s | %(name)-20s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d | %(message)s"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, TimedRotatingFileHandler) for h in root.handlers):
        console = logging.StreamHandler(sys.stderr)
        console.setLevel(level)
        console.setFormatter(logging.Formatter(fmt_console))
        root.addHandler(console)

    if not any(isinstance(h, TimedRotatingFileHandler) and getattr(h, '_baseFilename', '').endswith('tradingagents.log') for h in root.handlers):
        fh = TimedRotatingFileHandler(
            filename=Path(log_dir) / "tradingagents.log",
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter(fmt_file))
        fh.suffix = "%Y-%m-%d"
        root.addHandler(fh)

    if not any(isinstance(h, TimedRotatingFileHandler) and getattr(h, '_baseFilename', '').endswith('error.log') for h in root.handlers):
        eh = TimedRotatingFileHandler(
            filename=Path(log_dir) / "error.log",
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
        eh.setLevel(logging.WARNING)
        eh.setFormatter(logging.Formatter(fmt_file))
        eh.suffix = "%Y-%m-%d"
        root.addHandler(eh)

    for name, lvl in [
        ("urllib3", logging.WARNING),
        ("requests", logging.WARNING),
        ("httpx", logging.WARNING),
        ("httpcore", logging.WARNING),
        ("matplotlib", logging.WARNING),
    ]:
        logging.getLogger(name).setLevel(lvl)


def _run_check():
    from tradingagents_mcp.validators import check_health, build_config

    print("=" * 60)
    print("  TradingAgents A股 MCP 环境检查")
    print("=" * 60)

    health = check_health()
    config = build_config()

    print(f"\n📋 MCP Server: {health.get('mcp_server', 'unknown')}")

    print(f"\n🔑 LLM 配置:")
    print(f"   Provider: {config.get('llm_provider', '未配置')}")
    print(f"   Deep Think: {config.get('deep_think_llm', '未配置')}")
    print(f"   Quick Think: {config.get('quick_think_llm', '未配置')}")
    print(f"   API Key: {health.get('llm_api_key', 'unknown')}")

    print(f"\n📊 数据源:")
    for pkg in ["akshare", "timelyre"]:
        status = health.get(pkg, "unknown")
        icon = "✅" if status == "ok" else "❌"
        print(f"   {icon} {pkg}: {status}")

    all_ok = (
        health.get("mcp_server") == "ok"
        and "missing" not in str(health.get("llm_api_key", ""))
    )

    print(f"\n{'✅ 环境检查通过！' if all_ok else '⚠️  存在问题，请根据上述提示修复'}")
    print("=" * 60)

    return 0 if all_ok else 1


def _run_server():
    _setup_logging()

    from tradingagents_mcp.server import mcp

    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "9000"))
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        mcp.run(transport="stdio")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        sys.exit(_run_check())
    _run_server()


if __name__ == "__main__":
    main()
