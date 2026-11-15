#!/bin/bash
# Build the owner's fork and run it on loopback. Does not publish.
# A second invocation will not replace a process that is still starting.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "${MCP_SKIP_BUILD:-}" != "1" ]]; then
  "$ROOT/scripts/build_mcp.sh"
fi

BIN="${MCP_BIN:-$ROOT/runtime/bin/xiaohongshu-mcp}"
SESSION="$ROOT/runtime/session"
LOG_DIR="$ROOT/runtime/logs"
PID_FILE="$ROOT/runtime/mcp.pid"
LOCK_FILE="$ROOT/runtime/mcp.lock"
LISTEN="127.0.0.1:18060"
POLL_COUNT="${MCP_START_POLL_COUNT:-60}"
POLL_SECONDS="${MCP_START_POLL_SECONDS:-5}"

if [[ "$LISTEN" != "127.0.0.1:18060" ]]; then
  echo "refusing to bind MCP anywhere except 127.0.0.1:18060" >&2
  exit 2
fi

mkdir -p "$SESSION/home" "$SESSION/config" "$LOG_DIR" "$ROOT/runtime"
umask 077
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "another start_mcp.sh is already in progress; not launching a second process" >&2
  exit 1
fi

health_up() {
  curl -fs --max-time 3 -o /dev/null "http://${LISTEN}/health"
}

pid_alive() {
  local pid="$1" stat state
  [[ -n "$pid" && -r "/proc/${pid}/stat" ]] || return 1
  stat="$(cat "/proc/${pid}/stat")"
  state="${stat##*) }"
  state="${state%% *}"
  [[ -n "$state" && "$state" != "Z" ]]
}

read_pid() {
  if [[ -f "$PID_FILE" ]]; then
    tr -cd '0-9' < "$PID_FILE"
  fi
}

wait_for_health() {
  local pid="$1"
  local _
  for _ in $(seq 1 "$POLL_COUNT"); do
    if health_up; then
      return 0
    fi
    if [[ -n "$pid" ]] && ! pid_alive "$pid"; then
      return 1
    fi
    sleep "$POLL_SECONDS"
  done
  return 1
}

existing="$(read_pid || true)"
if pid_alive "$existing"; then
  echo "MCP pid ${existing} is already starting or running; not launching a second process"
  if wait_for_health "$existing"; then
    echo "health endpoint is up"
    exit 0
  fi
  if pid_alive "$existing"; then
    echo "MCP pid ${existing} is still running and health is not ready. Not launching another process." >&2
    exit 1
  fi
fi

if health_up; then
  echo "MCP already listening on ${LISTEN}; not launching a second process"
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
new_pid=$!
echo "$new_pid" > "$PID_FILE"
echo "started pid ${new_pid} on http://${LISTEN}"

if wait_for_health "$new_pid"; then
  echo "health endpoint is up"
  exit 0
fi

if pid_alive "$new_pid"; then
  echo "health endpoint not ready yet. The first start downloads the built-in browser (about 150MB) into the session cache. The recorded pid is still ${new_pid}; start will not replace it. Do not paste runtime/logs/mcp.log if it contains a session." >&2
  exit 1
fi

echo "MCP process exited before health. Inspect runtime/logs/mcp.log locally and do not paste session material." >&2
exit 1
