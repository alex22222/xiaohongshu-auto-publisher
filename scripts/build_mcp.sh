#!/bin/bash
# Build xiaohongshu-mcp from the owner's fork on this same host.
# Does not download the upstream release binary and does not publish.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="${MCP_RUNTIME_DIR:-$ROOT/runtime}"
SOURCE_URL="https://github.com/alex22222/xiaohongshu-mcp.git"
SOURCE_COMMIT="bb6fa2e208719ee634fec37881be29d3aa4699b3"
VERSION="v2.7.4"
SRC="$RUNTIME/src/xiaohongshu-mcp"
BIN="$RUNTIME/bin/xiaohongshu-mcp"
STAMP="$RUNTIME/bin/xiaohongshu-mcp.commit"
BUILD_LOCK="$RUNTIME/mcp-build.lock"

mkdir -p "$RUNTIME"
exec 8>"$BUILD_LOCK"
flock 8

if [[ -x "$BIN" && -f "$STAMP" ]] && [[ "$(cat "$STAMP")" == "$SOURCE_COMMIT" ]]; then
  echo "fork build already present for ${SOURCE_COMMIT}"
  exit 0
fi

mkdir -p "$RUNTIME/src" "$RUNTIME/bin"
if [[ ! -d "$SRC/.git" ]]; then
  rm -rf "$SRC"
  git init "$SRC"
  git -C "$SRC" remote add origin "$SOURCE_URL"
fi

# Compare the stored URL, not `git remote get-url`, which can rewrite in
# credentials. Never print the URL.
actual_url="$(git -C "$SRC" config --get remote.origin.url)"
case "$actual_url" in
  https://github.com/alex22222/xiaohongshu-mcp|https://github.com/alex22222/xiaohongshu-mcp.git)
    ;;
  *)
    echo "refusing checkout whose origin is not the owner fork" >&2
    exit 2
    ;;
esac

git -C "$SRC" fetch --quiet --depth 1 origin "$SOURCE_COMMIT"
git -C "$SRC" checkout --detach --force FETCH_HEAD
head="$(git -C "$SRC" rev-parse HEAD)"
if [[ "$head" != "$SOURCE_COMMIT" ]]; then
  echo "fork checkout is not the pinned v2.7.4 commit" >&2
  exit 2
fi

if ! command -v go >/dev/null 2>&1; then
  echo "Go is required to build the fork. go.mod asks for go1.27.3." >&2
  exit 1
fi

(
  cd "$SRC"
  GOTOOLCHAIN=go1.27.3 go build -trimpath -ldflags "-X main.version=${VERSION}" -o "$BIN" .
)
echo "$SOURCE_COMMIT" > "$STAMP"
chmod 755 "$BIN"
echo "built ${VERSION} from alex22222/xiaohongshu-mcp@${SOURCE_COMMIT}"
