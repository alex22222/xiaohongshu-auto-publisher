"""Publishing stays off, including after a draft is marked ready."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import draft_pipeline
import mcp_health
import publish_guard
from publish_guard import SHANGHAI

ENTRYPOINTS = [
    "src/xiaohongshu_full_auto_system_v3_complete.py",
    "src/xiaohongshu_publisher.py",
    "src/xiaohongshu_auto_scheduler.py",
    "src/xiaohongshu_auto_post.py",
    "src/xiaohongshu_auto_reply.py",
    "src/xiaohongshu_comment_reply_system.py",
    "src/run_comment_check.py",
]


def example_config():
    return publish_guard.load_config(ROOT / "config" / "config.json.example")


def test_config_keeps_publishing_off():
    config = example_config()
    assert config["publishing"]["enabled"] is False
    assert config["publishing"]["auto_post_approved_drafts"] is False
    assert config["schedule"]["enabled"] is False
    assert config["schedule"]["cron"] is None
    assert config["schedule"]["hours"] == []
    assert config["cadence"]["documented_only"] is True
    assert config["cadence"]["max_notes_per_day"] == 1
    assert config["cadence"]["min_hours_between_notes"] == 24
    assert config["cadence"]["daytime_start_hour"] == 8
    assert config["cadence"]["daytime_end_hour"] == 21
    assert config["mcp"]["version"] == "v2.7.4"
    assert config["mcp"]["base_url"] == "http://127.0.0.1:18060"
    assert publish_guard.PUBLISHING_ENABLED is False
    assert publish_guard.may_auto_post(config=config) is False


def test_daytime_window_is_documentation_only():
    noon = datetime(2026, 11, 15, 12, 0, tzinfo=SHANGHAI)
    early = datetime(2026, 11, 15, 7, 59, tzinfo=SHANGHAI)
    open_hour = datetime(2026, 11, 15, 8, 0, tzinfo=SHANGHAI)
    close_hour = datetime(2026, 11, 15, 21, 0, tzinfo=SHANGHAI)
    assert publish_guard.within_documented_daytime(noon) is True
    assert publish_guard.within_documented_daytime(early) is False
    assert publish_guard.within_documented_daytime(open_hour) is True
    assert publish_guard.within_documented_daytime(close_hour) is False
    assert publish_guard.may_auto_post(now=noon) is False


def test_ready_draft_does_not_publish(tmp_path):
    draft = draft_pipeline.create_draft("title", "body", tmp_path)
    draft = draft_pipeline.advance(draft["id"], draft_pipeline.REVIEW_PACKAGE, tmp_path)
    draft = draft_pipeline.advance(draft["id"], draft_pipeline.READY_TO_PUBLISH, tmp_path)
    assert draft["status"] == "ready_to_publish"
    assert draft["auto_post"] is False
    with pytest.raises(SystemExit) as caught:
        draft_pipeline.publish(draft["id"], tmp_path)
    assert caught.value.code == 2


def test_login_summary_drops_secrets():
    payload = {
        "success": True,
        "data": {
            "is_logged_in": True,
            "username": "secret-name",
            "user_id": "secret-id",
            "cookie": "secret-cookie",
            "img": "data:image/png;base64,AAAA",
        },
        "message": "secret-name",
    }
    summary = mcp_health.summarize_login_status(payload)
    blob = json.dumps(summary)
    assert summary == {"is_logged_in": True, "username_present": True}
    assert "secret-name" not in blob
    assert "secret-id" not in blob
    assert "secret-cookie" not in blob
    assert "AAAA" not in blob


def test_qr_writer_stores_png_and_hides_payload(tmp_path):
    png = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
        "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    payload = {
        "success": True,
        "data": {
            "timeout": "60s",
            "is_logged_in": False,
            "img": "data:image/png;base64," + png,
            "cookie": "secret-cookie",
        },
    }
    dest = tmp_path / "login-qr.png"
    summary = mcp_health.write_qr_png(payload, dest)
    blob = json.dumps(summary)
    assert summary["qr_written"] is True
    assert "secret-cookie" not in blob
    assert png not in blob
    assert dest.read_bytes().startswith(b"\x89PNG")


def test_publish_route_is_not_requested(monkeypatch):
    def fail_open(*_args, **_kwargs):
        raise AssertionError("network was used")

    monkeypatch.setattr(mcp_health.urllib.request, "urlopen", fail_open)
    with pytest.raises(SystemExit) as caught:
        mcp_health.get_json("/api/v1/publish", timeout=1)
    assert caught.value.code == 2
    assert "/api/v1/publish" in publish_guard.BLOCKED_HTTP_PATHS
    assert "publish_content" in publish_guard.BLOCKED_MCP_TOOLS


def test_health_summary_ignores_extra_fields():
    summary = mcp_health.summarize_health(
        {
            "success": True,
            "data": {
                "status": "healthy",
                "service": "xiaohongshu-mcp",
                "version": "v2.7.4",
                "cookie": "secret-cookie",
            },
        }
    )
    assert summary["ok"] is True
    assert summary["version"] == "v2.7.4"
    assert "secret-cookie" not in json.dumps(summary)
    assert summary["publishing_enabled"] is False
    assert summary["auto_post"] is False


@pytest.mark.parametrize("relative", ENTRYPOINTS)
def test_old_entrypoints_refuse(relative):
    proc = subprocess.run(
        [sys.executable, str(ROOT / relative)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert proc.returncode == 2
    assert "Refused" in proc.stderr


@pytest.mark.parametrize(
    "relative",
    ["src/xiaohongshu_post.sh", "src/xiaohongshu_random_publish.sh"],
)
def test_cron_helpers_refuse(relative):
    script = ROOT / relative
    text = script.read_text(encoding="utf-8")
    assert "sleep" not in text
    assert "crontab" not in text
    proc = subprocess.run(
        ["bash", str(script)],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert proc.returncode == 2
    assert "Refused" in proc.stderr


def test_pause_status_does_not_resume(tmp_path):
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["HOME"] = str(tmp_path)
    status = subprocess.run(
        [sys.executable, str(ROOT / "src" / "xiaohongshu_pause.py"), "status"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=env,
    )
    assert status.returncode == 0
    assert "publishing_enabled=false" in status.stdout
    assert "auto_post=false" in status.stdout

    resume = subprocess.run(
        [sys.executable, str(ROOT / "src" / "xiaohongshu_pause.py"), "resume"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=env,
    )
    assert resume.returncode == 2
    assert "Refused" in resume.stderr
    saved = json.loads((tmp_path / ".xiaohongshu_pause.json").read_text(encoding="utf-8"))
    assert saved["paused"] is True
