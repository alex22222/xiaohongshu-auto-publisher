#!/bin/bash
# Stop the MCP process started by scripts/start_mcp.sh.
# The pid file stays until that process has exited, so a restart cannot
# attach to a listener that is already going away.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="${MCP_RUNTIME_DIR:-$ROOT/runtime}"
PID_FILE="$RUNTIME/mcp.pid"
HEALTH_URL="${MCP_HEALTH_URL:-http://127.0.0.1:18060/health}"

health_up() {
  curl -fs --max-time 1 -o /dev/null "$HEALTH_URL"
}

pid_alive() {
  local pid="$1" stat state
  [[ -n "$pid" && -r "/proc/${pid}/stat" ]] || return 1
  stat="$(cat "/proc/${pid}/stat")"
  state="${stat##*) }"
  state="${state%% *}"
  [[ -n "$state" && "$state" != "Z" ]]
}

if [[ ! -f "$PID_FILE" ]]; then
  echo "no pid file; nothing stopped"
  exit 0
fi

pid="$(tr -cd '0-9' < "$PID_FILE")"
if [[ -z "$pid" ]]; then
  rm -f "$PID_FILE"
  echo "pid file was empty"
  exit 0
fi

if pid_alive "$pid"; then
  kill "$pid" || true
  for _ in $(seq 1 50); do
    if ! pid_alive "$pid"; then
      break
    fi
    sleep 0.2
  done
  if pid_alive "$pid"; then
    echo "pid ${pid} did not exit after SIGTERM; pid file kept" >&2
    exit 1
  fi
  echo "stopped pid ${pid}"
else
  echo "pid ${pid} was not running"
fi

rm -f "$PID_FILE"

for _ in $(seq 1 50); do
  if ! health_up; then
    exit 0
  fi
  sleep 0.2
done

echo "health still responds after pid ${pid} exited" >&2
exit 1
