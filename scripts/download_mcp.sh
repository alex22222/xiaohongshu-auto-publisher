#!/bin/bash
# The upstream release binary is not the source of truth.
echo "Refused: do not download a disconnected upstream binary. Use scripts/build_mcp.sh." >&2
exit 2
