#!/bin/bash
# Build the owner's fork and run it on loopback. Does not publish.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$ROOT/scripts/build_mcp.sh"

BIN="$ROOT/runtime/bin/xiaohongshu-mcp"
SESSION="$ROOT/runtime/session"
LOG_DIR="$ROOT/runtime/logs"
PID_FILE="$ROOT/runtime/mcp.pid"
LISTEN="127.0.0.1:18060"
if [[ "$LISTEN" != "127.0.0.1:18060" ]]; then
  echo "refusing to bind MCP anywhere except 127.0.0.1:18060" >&2
  exit 2
fi

mkdir -p "$SESSION/home" "$SESSION/config" "$LOG_DIR"
umask 077

if curl -fs --max-time 3 -o /dev/null "http://127.0.0.1:18060/health"; then
  echo "MCP already listening on 127.0.0.1:18060"
  exit 0
fi

# Always pin the session file inside runtime/session. A copied Mac path
# is not used. AUTH_TOKEN is read by the binary only when already exported;
# this script does not set it and does not print it.
export COOKIES_PATH="$SESSION/cookies.json"
export HOME="$SESSION/home"
export XDG_CONFIG_HOME="$SESSION/config"
export XDG_CACHE_HOME="$SESSION/home/.cache"

cd "$SESSION"
nohup "$BIN" -headless=true -port "$LISTEN" >> "$LOG_DIR/mcp.log" 2>&1 &
echo $! > "$PID_FILE"
echo "started pid $(cat "$PID_FILE") on http://127.0.0.1:18060"

for _ in $(seq 1 60); do
  if curl -fs --max-time 3 -o /dev/null "http://127.0.0.1:18060/health"; then
    echo "health endpoint is up"
    exit 0
  fi
  if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "MCP process exited before health. Inspect runtime/logs/mcp.log locally and do not paste session material." >&2
    exit 1
  fi
  sleep 5
done

echo "health endpoint not ready yet. The first start downloads the built-in browser (about 150MB) into the session cache. Re-run scripts/health_check.py. Do not paste runtime/logs/mcp.log if it contains a session." >&2
exit 1
