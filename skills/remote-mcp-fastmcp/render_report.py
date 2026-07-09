#!/usr/bin/env python3
"""将 trading_agent 的 JSON 结果使用 template.html 渲染并打开

用法:
  cat result.json | python3 render_report.py                    # 写入 /tmp 并浏览器打开
  cat result.json | python3 render_report.py --stdout           # 输出到 stdout（供侧边栏预览）
  cat result.json | python3 render_report.py -o report.html     # 输出到指定文件
  cat result.json | python3 render_report.py --stdout --no-open # 输出到 stdout 不打开浏览器
"""
import json, os, sys, webbrowser, tempfile, argparse
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = SKILL_DIR / "template.html"


def extract_report_data(data: dict) -> dict:
    """从 trading_agent 返回的数据中提取所有报告字段"""
    result = data.get("data", data)
    ctx = result.get("ctx", {})

    # 基础信息
    info = {
        "company_name": result.get("company_name", ctx.get("company_name", "未知")),
        "symbol": ctx.get("symbol", "未知"),
        "trade_date": ctx.get("trade_date", ""),
    }

    # 四大分析师报告
    for key in ["market_report", "fundamentals_report", "news_report", "sentiment_report"]:
        info[key] = result.get(key, "")

    # 多空辩论
    debate = result.get("investment_debate", {})
    for key in ["bull_history", "bear_history", "judge_decision"]:
        info[key] = debate.get(key, "")

    # 交易员投资计划
    info["trader_investment_plan"] = result.get("trader_investment_plan", "")

    # 风险辩论
    risk = result.get("risk_debate", {})
    for key in ["aggressive_history", "conservative_history", "neutral_history"]:
        info[key] = risk.get(key, "")
    info["risk_judge_decision"] = risk.get("judge_decision", "")

    # 最终决策
    info["investment_plan"] = result.get("investment_plan", "")
    info["final_trade_decision"] = result.get("final_trade_decision", "")

    return info


def render(data: dict) -> str:
    """将 JSON 数据渲染为完整的 HTML 字符串"""
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    reports = extract_report_data(data)
    company = reports["company_name"]
    symbol = reports["symbol"]

    # 中英文占位符映射表
    placeholder_map = {
        # 英文占位符（下划线大写）
        "___COMPANY_NAME___": company,
        "___SYMBOL___": symbol,
        "___MARKET_REPORT___": reports.get("market_report", ""),
        "___FUNDAMENTALS_REPORT___": reports.get("fundamentals_report", ""),
        "___NEWS_REPORT___": reports.get("news_report", ""),
        "___SENTIMENT_REPORT___": reports.get("sentiment_report", ""),
        "___BULL_HISTORY___": reports.get("bull_history", ""),
        "___BEAR_HISTORY___": reports.get("bear_history", ""),
        "___JUDGE_DECISION___": reports.get("judge_decision", ""),
        "___TRADER_INVESTMENT_PLAN___": reports.get("trader_investment_plan", ""),
        "___AGGRESSIVE_HISTORY___": reports.get("aggressive_history", ""),
        "___CONSERVATIVE_HISTORY___": reports.get("conservative_history", ""),
        "___NEUTRAL_HISTORY___": reports.get("neutral_history", ""),
        "___RISK_JUDGE_DECISION___": reports.get("risk_judge_decision", ""),
        "___INVESTMENT_PLAN___": reports.get("investment_plan", ""),
        "___FINAL_TRADE_DECISION___": reports.get("final_trade_decision", ""),
        # 中文占位符（兼容旧模板）
        "___技术分析报告内容___": reports.get("market_report", ""),
        "___基本面分析报告内容___": reports.get("fundamentals_report", ""),
        "___新闻分析报告内容___": reports.get("news_report", ""),
        "___情绪分析报告内容___": reports.get("sentiment_report", ""),
        "___看涨研究员观点___": reports.get("bull_history", ""),
        "___看跌研究员观点___": reports.get("bear_history", ""),
        "___研究主管裁决___": reports.get("judge_decision", ""),
        "___交易员投资计划___": reports.get("trader_investment_plan", ""),
        "___激进风控员观点___": reports.get("aggressive_history", ""),
        "___保守风控员观点___": reports.get("conservative_history", ""),
        "___中性风控员观点___": reports.get("neutral_history", ""),
        "___投资组合经理风险裁决___": reports.get("risk_judge_decision", ""),
        "___最终投资计划___": reports.get("investment_plan", ""),
        "___最终交易决策___": reports.get("final_trade_decision", ""),
    }

    # 批量替换
    for placeholder, value in placeholder_map.items():
        html = html.replace(placeholder, str(value))

    return html


def main():
    parser = argparse.ArgumentParser(description="渲染 trading_agent 分析报告为 HTML")
    parser.add_argument("--stdout", action="store_true", help="输出到 stdout 而不是文件")
    parser.add_argument("-o", "--output", type=str, help="输出文件路径")
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    raw = sys.stdin.read()
    if not raw:
        print("错误: 无输入数据（请通过管道传递 JSON）", file=sys.stderr)
        sys.exit(1)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败 - {e}", file=sys.stderr)
        sys.exit(1)

    html = render(parsed)

    # 输出模式选择
    if args.stdout:
        # 输出到 stdout（侧边栏/管道使用）
        sys.stdout.write(html)
    elif args.output:
        # 输出到指定文件
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"报告已保存: {args.output}")
        if not args.no_open:
            webbrowser.open(f"file://{os.path.abspath(args.output)}")
    else:
        # 默认：写入临时目录并打开浏览器
        reports = extract_report_data(parsed)
        symbol = reports.get("symbol", "unknown")
        path = os.path.join(tempfile.gettempdir(), f"trading_report_{symbol}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"报告已保存: {path}")
        if not args.no_open:
            webbrowser.open(f"file://{path}")


if __name__ == "__main__":
    main()