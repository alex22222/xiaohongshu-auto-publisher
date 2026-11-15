#!/bin/bash
# Download the official xiaohongshu-mcp v2.7.4 Linux binary.
# The binary is not committed. Checksum is config/mcp-v2.7.4.sha256.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/runtime/bin"
FILE="xiaohongshu-mcp-linux-amd64"
URL="https://github.com/xpzouying/xiaohongshu-mcp/releases/download/v2.7.4/${FILE}"
SUMS="$ROOT/config/mcp-v2.7.4.sha256"
OUT="$DEST/$FILE"

EXPECTED="$(awk -v name="$FILE" '$2 == name { print $1 }' "$SUMS")"
if [[ -z "$EXPECTED" ]]; then
  echo "missing checksum for ${FILE}" >&2
  exit 1
fi

mkdir -p "$DEST"

if [[ -f "$OUT" ]]; then
  got="$(sha256sum "$OUT" | awk '{ print $1 }')"
  if [[ "$got" == "$EXPECTED" ]]; then
    echo "official v2.7.4 binary already present"
    exit 0
  fi
  echo "checksum mismatch, downloading again" >&2
  rm -f "$OUT"
fi

curl -fL --retry 3 --retry-delay 2 -o "$OUT.partial" "$URL"
got="$(sha256sum "$OUT.partial" | awk '{ print $1 }')"
if [[ "$got" != "$EXPECTED" ]]; then
  rm -f "$OUT.partial"
  echo "checksum mismatch for official binary" >&2
  exit 1
fi
mv "$OUT.partial" "$OUT"
chmod 755 "$OUT"
echo "downloaded official v2.7.4 linux-amd64"
