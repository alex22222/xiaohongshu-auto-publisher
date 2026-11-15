#!/usr/bin/env python3
"""Login and process checks against official xiaohongshu-mcp.

Allowed calls are GET /health, GET /api/v1/login/status, and
GET /api/v1/login/qrcode. Responses are reduced to booleans and a
local PNG path. Cookie files, tokens, account ids, and QR payloads
are not printed.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import publish_guard

ALLOWED_GET_PATHS = (
    "/health",
    "/api/v1/login/status",
    "/api/v1/login/qrcode",
)

MAX_BODY_BYTES = 2_000_000


class HealthError(RuntimeError):
    pass


def _headers() -> dict:
    headers = {"Accept": "application/json"}
    token = os.environ.get("AUTH_TOKEN", "")
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


def get_json(path: str, timeout: float) -> dict:
    if path not in ALLOWED_GET_PATHS:
        publish_guard.refuse(f"HTTP GET {path}")
    url = publish_guard.mcp_base_url() + path
    request = urllib.request.Request(url, headers=_headers(), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_BODY_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise HealthError(f"HTTP {exc.code} for {path}") from None
    except urllib.error.URLError:
        raise HealthError(f"unreachable: {path}") from None
    if len(raw) > MAX_BODY_BYTES:
        raise HealthError(f"response too large for {path}")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HealthError(f"non-json response for {path}") from None
    if not isinstance(payload, dict):
        raise HealthError(f"unexpected response for {path}")
    return payload


def summarize_health(payload: dict) -> dict:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        data = {}
    status = data.get("status")
    service = data.get("service")
    version = data.get("version")
    safe_version = (
        version
        if isinstance(version, str) and version.isascii() and len(version) <= 32
        else None
    )
    ok = (
        payload.get("success") is True
        and status == "healthy"
        and service == "xiaohongshu-mcp"
    )
    return {
        "ok": ok,
        "status": "healthy" if ok else "unhealthy",
        "service": "xiaohongshu-mcp" if service == "xiaohongshu-mcp" else None,
        "version": safe_version if ok else None,
        "publishing_enabled": False,
        "auto_post": False,
    }


def summarize_login_status(payload: dict) -> dict:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return {"is_logged_in": None, "username_present": False}
    logged = data.get("is_logged_in")
    username = data.get("username")
    return {
        "is_logged_in": logged if isinstance(logged, bool) else None,
        "username_present": isinstance(username, str) and bool(username),
    }


def write_qr_png(payload: dict, dest: Path) -> dict:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise HealthError("login qr response withheld")
    logged = data.get("is_logged_in")
    timeout = data.get("timeout") if isinstance(data.get("timeout"), str) else None
    img = data.get("img") if isinstance(data.get("img"), str) else ""
    summary = {
        "is_logged_in": logged if isinstance(logged, bool) else None,
        "timeout": timeout,
        "qr_written": False,
        "qr_path": None,
    }
    if not img:
        return summary
    encoded = img.split(",", 1)[1] if img.startswith("data:") and "," in img else img
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise HealthError("login qr image could not be decoded") from None
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HealthError("login qr image was not a png")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    os.chmod(dest, 0o600)
    summary["qr_written"] = True
    summary["qr_path"] = str(dest)
    return summary


def health_report(login_status: bool = False) -> dict:
    health = summarize_health(get_json("/health", timeout=5))
    report = {
        "health": health,
        "cadence": publish_guard.describe_cadence(),
        "publishing_enabled": False,
        "auto_post": False,
        "mcp_base_url": publish_guard.mcp_base_url(),
    }
    if login_status:
        try:
            report["login"] = summarize_login_status(
                get_json("/api/v1/login/status", timeout=90)
            )
        except HealthError as exc:
            report["login"] = {"is_logged_in": None, "error": str(exc)}
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check official MCP health. Optionally check login status. Never publishes."
    )
    parser.add_argument(
        "--login-status",
        action="store_true",
        help="GET /api/v1/login/status and print only a redacted boolean",
    )
    args = parser.parse_args(argv)
    try:
        report = health_report(login_status=args.login_status)
    except HealthError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "publishing_enabled": False,
                    "auto_post": False,
                },
                ensure_ascii=False,
            )
        )
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["health"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
