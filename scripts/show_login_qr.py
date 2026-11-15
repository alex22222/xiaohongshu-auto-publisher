#!/usr/bin/env python3
"""Write a login QR png for the owner to scan. Does not print the image or cookies."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import publish_guard
from mcp_health import HealthError, get_json, write_qr_png


def main() -> int:
    dest = publish_guard.repo_root() / "runtime" / "session" / "login-qr.png"
    try:
        summary = write_qr_png(get_json("/api/v1/login/qrcode", timeout=90), dest)
    except HealthError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(
        "Scan the png with the Xiaohongshu mobile app on the same account. "
        "Do not commit runtime/session or paste the image into chat.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
