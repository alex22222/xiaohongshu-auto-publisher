#!/usr/bin/env python3
"""Cloud publishing kill switch.

This module has no allow branch. Config cannot turn posting back on.
An approved draft still does not auto-post.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Code-level switch. refuse() does not consult this to permit traffic.
PUBLISHING_ENABLED = False

SHANGHAI = timezone(timedelta(hours=8))

BLOCKED_HTTP_PATHS = (
    "/api/v1/publish",
    "/api/v1/publish_video",
    "/api/v1/feeds/list",
    "/api/v1/feeds/search",
    "/api/v1/feeds/detail",
    "/api/v1/feeds/comment",
    "/api/v1/feeds/comment/reply",
    "/api/v1/feeds/like",
    "/api/v1/feeds/favorite",
    "/api/v1/user/profile",
    "/api/v1/user/me",
    "/api/v1/notifications/unread",
    "/api/v1/notifications/list",
    "/api/v1/notifications/reply",
    "/api/v1/notifications/like",
    "/api/v1/login/cookies",
)

BLOCKED_MCP_TOOLS = (
    "publish_content",
    "publish_with_video",
    "list_feeds",
    "search_feeds",
    "get_feed_detail",
    "post_comment_to_feed",
    "reply_comment_in_feed",
    "like_feed",
    "favorite_feed",
    "user_profile",
    "delete_cookies",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_config(path: Path | None = None) -> dict:
    root = repo_root()
    if path is None:
        local = root / "config" / "config.json"
        path = local if local.exists() else root / "config" / "config.json.example"
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("config root must be an object")
    return data


def mcp_base_url(config: dict | None = None) -> str:
    override = os.environ.get("XHS_MCP_BASE_URL", "").strip()
    if override:
        return override.rstrip("/")
    data = config if config is not None else load_config()
    mcp = data.get("mcp") if isinstance(data.get("mcp"), dict) else {}
    base = str(mcp.get("base_url") or "http://127.0.0.1:18060").rstrip("/")
    return base


def describe_cadence(config: dict | None = None) -> dict:
    """Return the later cadence. It is documentation, not a poster."""
    data = config if config is not None else load_config()
    cadence = data.get("cadence") if isinstance(data.get("cadence"), dict) else {}
    return {
        "documented_only": True,
        "enforced_as_poster": False,
        "max_notes_per_day": int(cadence.get("max_notes_per_day", 1)),
        "min_hours_between_notes": int(cadence.get("min_hours_between_notes", 24)),
        "daytime_only": True,
        "timezone": "Asia/Shanghai",
        "daytime_start_hour": int(cadence.get("daytime_start_hour", 8)),
        "daytime_end_hour": int(cadence.get("daytime_end_hour", 21)),
        "auto_post_approved_drafts": False,
    }


def within_documented_daytime(moment: datetime, config: dict | None = None) -> bool:
    """Whether a clock time sits inside the documented daytime window."""
    cadence = describe_cadence(config)
    if moment.tzinfo is None:
        local = moment.replace(tzinfo=SHANGHAI)
    else:
        local = moment.astimezone(SHANGHAI)
    start = cadence["daytime_start_hour"]
    end = cadence["daytime_end_hour"]
    return start <= local.hour < end


def may_auto_post(*_args, **_kwargs) -> bool:
    """Approved drafts do not auto-post. This stays false."""
    return False


def refuse(action: str) -> None:
    """Stop a publish, comment, like, search, or cron resume.

    There is no success path. PUBLISHING_ENABLED is not an allow flag.
    """
    print(
        f"Refused {action}: publishing, comments, likes, and other "
        "Xiaohongshu write or interaction traffic are disabled. "
        "An approved draft does not auto-post. "
        "See docs/cloud-architecture.md.",
        file=sys.stderr,
    )
    raise SystemExit(2)
