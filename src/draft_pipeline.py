#!/usr/bin/env python3
"""Local draft pipeline.

content_draft -> review_package -> ready_to_publish.

The publish command always refuses. Ready drafts stay on disk.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import publish_guard

CONTENT_DRAFT = "content_draft"
REVIEW_PACKAGE = "review_package"
READY_TO_PUBLISH = "ready_to_publish"
ORDER = (CONTENT_DRAFT, REVIEW_PACKAGE, READY_TO_PUBLISH)


def drafts_dir() -> Path:
    override = os.environ.get("DRAFTS_DIR", "").strip()
    if override:
        return Path(override)
    return publish_guard.repo_root() / "runtime" / "drafts"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _path(draft_id: str, directory: Path | None = None) -> Path:
    if not draft_id or "/" in draft_id or draft_id.startswith("."):
        raise ValueError("invalid draft id")
    return (directory or drafts_dir()) / f"{draft_id}.json"


def _read(draft_id: str, directory: Path | None = None) -> dict:
    path = _path(draft_id, directory)
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("draft must be an object")
    return data


def _write(draft: dict, directory: Path | None = None) -> Path:
    directory = directory or drafts_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = _path(str(draft["id"]), directory)
    path.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def create_draft(title: str, body: str, directory: Path | None = None) -> dict:
    draft = {
        "id": uuid.uuid4().hex,
        "status": CONTENT_DRAFT,
        "title": title,
        "body": body,
        "created_at": _now(),
        "updated_at": _now(),
        "auto_post": False,
    }
    _write(draft, directory)
    return draft


def advance(draft_id: str, target: str, directory: Path | None = None) -> dict:
    if target not in ORDER:
        raise ValueError("unknown status")
    draft = _read(draft_id, directory)
    current = draft.get("status")
    if current not in ORDER or target not in ORDER:
        raise ValueError("draft status is not in the pipeline")
    if ORDER.index(target) != ORDER.index(current) + 1:
        raise ValueError(f"cannot move {current} to {target}")
    draft["status"] = target
    draft["updated_at"] = _now()
    draft["auto_post"] = False
    _write(draft, directory)
    return draft


def publish(draft_id: str, directory: Path | None = None) -> None:
    """Owner click is not wired. Ready drafts are not posted."""
    del directory
    del draft_id
    publish_guard.refuse("publish ready draft")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Draft pipeline. Publish is refused.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    init_cmd = sub.add_parser("init", help="Write a content draft")
    init_cmd.add_argument("--title", required=True)
    init_cmd.add_argument("--body", required=True)

    review_cmd = sub.add_parser("review", help="Mark a content draft as a review package")
    review_cmd.add_argument("--id", required=True)

    ready_cmd = sub.add_parser("ready", help="Mark a review package ready to publish")
    ready_cmd.add_argument("--id", required=True)

    show_cmd = sub.add_parser("show", help="Print one draft")
    show_cmd.add_argument("--id", required=True)

    publish_cmd = sub.add_parser("publish", help="Refused. Does not post.")
    publish_cmd.add_argument("--id", required=True)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "init":
            draft = create_draft(args.title, args.body)
        elif args.cmd == "review":
            draft = advance(args.id, REVIEW_PACKAGE)
        elif args.cmd == "ready":
            draft = advance(args.id, READY_TO_PUBLISH)
        elif args.cmd == "show":
            draft = _read(args.id)
        else:
            publish(args.id)
            return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"id": draft["id"], "status": draft["status"], "auto_post": False}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
