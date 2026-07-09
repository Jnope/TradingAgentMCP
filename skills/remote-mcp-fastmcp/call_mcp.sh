#!/bin/bash
# Usage: ./call_mcp.sh <tool_name> '<json_args>'
# Example: ./call_mcp.sh agent_status '{}'
# Example: ./call_mcp.sh market_analyst '{"symbol":"688031","trade_date":"2026-07-08"}'
# Example: ./call_mcp.sh trading_agent '{"symbol":"688031","trade_date":"2026-07-08","detail":false}'
#
# 输出模式（由 TOOL_NAME 自动确定）：
#   - trading_agent          → 打印原始内层 JSON（供 render_report.py 管道使用）
#   - agent_status           → 打印格式化状态信息
#   - 其他工具 (单分析师)    → 打印对应 *_report 文本（直接可读）

MCP_URL="http://172.18.192.76:19876/mcp"
TOOL_NAME="$1"
ARGS="$2"

# ─── 步骤1: 初始化，获取 Session ID ───
TMP=$(mktemp)
curl -s -D "$TMP" -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"call_mcp.sh","version":"1.0"}}}' > /dev/null

SID=$(grep -i 'mcp-session-id' "$TMP" | tr -d '\r' | awk '{print $2}')
rm -f "$TMP"

if [ -z "$SID" ]; then
  echo '{"success":false,"error":"无法获取 Session ID"}'
  exit 1
fi

# ─── 步骤2: 发送 initialized 通知 ───
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' > /dev/null

# ─── 步骤3: 流式调用工具，逐行处理 SSE 响应 ───
# -N 禁用 curl 输出缓冲，配合 while read 实现实时处理
curl -s -N -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SID" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"$TOOL_NAME\",\"arguments\":$ARGS}}" | \

while IFS= read -r line; do
  # 跳过空行和 ping 行
  [[ -z "$line" ]] && continue
  [[ "$line" =~ ^:\ ping ]] && continue
  # 跳过 event: 行（所有事件都是 event: message，无需特殊处理）
  [[ "$line" =~ ^event: ]] && continue

  # 只处理 data: 行
  if [[ "$line" =~ ^data:\ (.*)$ ]]; then
    data="${BASH_REMATCH[1]}"

    # 检查是否是进度通知（notifications/message）
    if echo "$data" | grep -q '"notifications/message"'; then
      # 提取进度文本并显示到 stderr
      echo "$data" | python3 -c '
import sys, json
try:
    msg = json.loads(sys.stdin.read())
    info = msg.get("params", {}).get("data", "")
    if info:
        print(f"\033[33m⏳ {info}\033[0m", file=sys.stderr)
except:
    pass
' 2>/dev/null
      continue
    fi

    # 检查是否是最终结果（包含 "result" 且有 "id"）
    if echo "$data" | grep -q '"result"'; then
      # ── 根据 TOOL_NAME 选择输出模式 ──
      if [ "$TOOL_NAME" = "trading_agent" ]; then
        # 全量分析 → 输出原始内层 JSON，供 render_report.py 管道使用
        echo "$data" | python3 -c '
import sys, json
msg = json.loads(sys.stdin.read())
if "result" in msg:
    for c in msg["result"].get("content", []):
        if c.get("type") == "text":
            print(c["text"])
'
      elif [ "$TOOL_NAME" = "agent_status" ]; then
        # 健康检查 → 格式化输出状态信息
        echo "$data" | python3 -c '
import sys, json
msg = json.loads(sys.stdin.read())
if "result" in msg:
    for c in msg["result"].get("content", []):
        if c.get("type") == "text":
            inner = json.loads(c["text"])
            if inner.get("success"):
                data = inner.get("data", {})
                h = data.get("health", {})
                print("=== TradingAgents 服务状态 ===")
                for k, v in h.items():
                    status = "✅" if v == "ok" else "❌"
                    print(f"  {status} {k}: {v}")
                print(f"  LLM: {data.get("llm_provider", "?")} / {data.get("deep_think_llm", "?")}")
                tools = data.get("available_tools", {})
                if tools:
                    print("\n=== 可用工具 ===")
                    for name, desc in tools.items():
                        print(f"  · {name}: {desc}")
            else:
                print("❌ 错误:", inner.get("error", "未知"))
'
      else
        # 单分析工具 → 提取 *_report 字段，直接输出可读文本
        echo "$data" | python3 -c '
import sys, json
msg = json.loads(sys.stdin.read())
if "result" in msg:
    for c in msg["result"].get("content", []):
        if c.get("type") == "text":
            inner = json.loads(c["text"])
            if inner.get("success"):
                data = inner.get("data", {})
                # 动态查找 *_report 字段
                report_keys = [k for k in data if k.endswith("_report")]
                if report_keys:
                    for k in report_keys:
                        print(data[k])
                else:
                    # 没有报告字段，输出完整 JSON
                    print(json.dumps(inner, ensure_ascii=False, indent=2))
            else:
                print("❌ 错误:", inner.get("error", "未知"))
'
      fi
      break
    fi
  fi
done
