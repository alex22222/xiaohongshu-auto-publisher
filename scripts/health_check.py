#!/usr/bin/env python3
"""Process health check, and optional redacted login status. Never publishes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcp_health import main

if __name__ == "__main__":
    sys.exit(main())
