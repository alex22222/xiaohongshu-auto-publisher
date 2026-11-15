#!/bin/bash
# Stop the MCP process started by scripts/start_mcp.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$ROOT/runtime/mcp.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "no pid file; nothing stopped"
  exit 0
fi

pid="$(cat "$PID_FILE")"
if kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  echo "stopped pid $pid"
else
  echo "pid $pid was not running"
fi
rm -f "$PID_FILE"
