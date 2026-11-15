# Cloud architecture

English summary: publishing stays off. This host builds [alex22222/xiaohongshu-mcp](https://github.com/alex22222/xiaohongshu-mcp) at `bb6fa2e208719ee634fec37881be29d3aa4699b3` (fork `main`, the same commit as upstream v2.7.4 on 2026-11-10) and runs that process on `127.0.0.1:18060`. The auto-publisher talks only to that loopback address. The two GitHub repositories stay separate. The owner is the only person who may publish, and that click is not wired. A ready draft does not auto-post. The old cron stays uninstalled. It once posted 3 notes in about 26 minutes.

GitHub `main` may be older than `/Users/henry/projects/xiaohongshu_auto`. That Mac tree was not readable from this change. Treat the generators and Excel paths in this checkout as incomplete. This document does not try to reconstruct them.

The Mac runtime at `/Users/henry/projects/xiaohongshu-mcp` (Cursor `mcp.json` → `http://localhost:18060/mcp`) is no longer the dependency. Stop that process before a cloud login. One Xiaohongshu account cannot stay signed in on two web clients; the mobile app can stay signed in.

## Pipeline

```
content draft  ->  review package  ->  ready-to-publish draft  ->  owner clicks Publish
                                                                   |
                                                                   +-- not implemented
                                                                       client exits 2
```

| Stage | Status | Where it lives | Who acts |
| --- | --- | --- | --- |
| Content draft | `content_draft` | `runtime/drafts/<id>.json` (gitignored) | Whoever prepares the note |
| Review package | `review_package` | same file | Reviewer reads title and body locally |
| Ready to publish | `ready_to_publish` | same file, `auto_post: false` | Nobody posts |
| Publish | refused | no HTTP call | Owner, later, on a change that is not this one |

Commands:

```bash
python3 src/draft_pipeline.py init --title "标题" --body "正文"
python3 src/draft_pipeline.py review --id <id>
python3 src/draft_pipeline.py ready --id <id>
python3 src/draft_pipeline.py publish --id <id>   # exits 2, no request
```

`publish` refuses even when the draft is `ready_to_publish`. There is no scheduler behind it.

## MCP from the owner's fork

Source of truth: [alex22222/xiaohongshu-mcp](https://github.com/alex22222/xiaohongshu-mcp), commit `bb6fa2e208719ee634fec37881be29d3aa4699b3`. That commit is `main` on the fork and the same commit upstream tagged [v2.7.4](https://github.com/xpzouying/xiaohongshu-mcp/releases/tag/v2.7.4) on 2026-11-10. The fork does not currently have a tag named `v2.7.4`, so the build pins the commit instead of a tag. This auto-publisher repo does not vendor the MCP source and does not open changes against the fork.

| Item | Value |
| --- | --- |
| Checkout | `runtime/src/xiaohongshu-mcp` (gitignored), remote must be the fork |
| Build | `GOTOOLCHAIN=go1.27.3 go build -ldflags "-X main.version=v2.7.4"` via `scripts/build_mcp.sh` |
| Binary | `runtime/bin/xiaohongshu-mcp` on this same host |
| Process | one long-running process, started by `scripts/start_mcp.sh` |
| Flags | `-headless=true -port 127.0.0.1:18060` |
| Listen | loopback only. The program's default `:18060` binds every interface; this script does not use that default |
| MCP URL | `http://127.0.0.1:18060/mcp` |
| Health | `GET /health` (no Xiaohongshu call) |
| Login status | `GET /api/v1/login/status` (reads the session; does not post) |
| Login QR | `GET /api/v1/login/qrcode` (owner step on the durable host; image stays on disk) |

`scripts/download_mcp.sh` exits 2. It does not fetch the upstream release tarball.

The first start downloads the built-in browser `148.0.7778.215` (about 150MB) from `https://cdn.one-world.ai/browsers`, checks its checksum, and caches it under `$XDG_CACHE_HOME/xiaohongshu-mcp/browser/148.0.7778.215`. The start script sets `XDG_CACHE_HOME` to `runtime/session/home/.cache`. The fork's v2.7.4 tree supports Linux x64. It does not ship a Linux ARM64 browser.

`scripts/start_mcp.sh` does not pass `-token` on the command line. If `AUTH_TOKEN` is already in the environment, the server enables `Authorization: Bearer`. Leave it unset while the port is loopback-only. Do not write the token into config or logs.

The built server still has publish, comment, and like routes. This repo never calls them. Do not expose port 18060, and do not add a Cursor `mcp.json` that loads those tools. There is no second host and no public bind.

## Session files

v2.7.4 resolves the cookie file in this order (`cookies.GetCookiesFilePath`):

1. `COOKIES_PATH` if set
2. `./cookies.json` if that file already exists
3. `$TMPDIR/cookies.json` if that file already exists
4. otherwise `./cookies.json` in the process working directory

The v2.7.4 release text also mentions `~/.xiaohongshu/cookies.json`. The source above does not use that path. `scripts/start_mcp.sh` always sets `COOKIES_PATH` to `runtime/session/cookies.json` and uses that directory as the working directory, so a stray file cannot land in the git root.

The file is a v2 session object: version, fingerprint seed, timestamp, and cookies. The whole file is a secret. `runtime/` is gitignored. Do not copy a Mac cookie file into git, chat, or the cloud host. Stop the Mac server, then sign in once on the cloud host with the QR. Signing in on two web clients logs one of them out.

## How this repo is wired

`src/publish_guard.py` is the client switch.

- `XHS_MCP_BASE_URL`, or `mcp.base_url` in config, default `http://127.0.0.1:18060` on the cloud host.
- `refuse()` has no allow branch. `PUBLISHING_ENABLED` is not consulted to permit a call.
- `may_auto_post()` is always false, including inside the documented daytime window, including when a draft is ready.
- Old entry points call `refuse()` before any Xiaohongshu request: the v3 publisher, `xiaohongshu_publisher.py`, the scheduler, `xiaohongshu_auto_post.py`, both comment scripts, `run_comment_check.py`, and the two shell cron helpers.
- `xiaohongshu_pause.py resume` does not clear the pause, and an expired pause file does not auto-resume. That expiry path is what let a timer start posting again.
- Comment and search helpers refuse as well. Health checks do not use them.

Config keys `publishing.enabled` and `schedule.enabled` are false in `config/config.json.example`. Changing them to true does not post, because the code never reads them as permission.

## Start and health check

On the cloud host (Linux x64), from this repo:

```bash
chmod +x scripts/*.sh scripts/*.py
./scripts/start_mcp.sh
python3 scripts/health_check.py
python3 scripts/health_check.py --login-status
./scripts/stop_mcp.sh
```

`health_check.py` prints `ok`, `publishing_enabled: false`, and `auto_post: false`. With `--login-status` it adds `is_logged_in` and `username_present`. It does not print the account name, user id, cookies, or the raw body.

Expect `is_logged_in: false` until the owner finishes the QR step. A failure to reach `/health` usually means the browser download is still running or the process exited. Read `runtime/logs/mcp.log` on the host. Do not paste that log if it contains a session.

These commands do not call `/api/v1/publish`, `publish_content`, or `publish_with_video`.

## Owner login (blocked until the owner does it)

This environment cannot finish login. The QR has to be scanned by the account owner on the durable cloud host, and the session has to stay in that host's `runtime/session/`.

1. On the Mac, stop the process from `/Users/henry/projects/xiaohongshu-mcp`. Disable the Cursor `mcp.json` entry that points at `http://localhost:18060/mcp` on the Mac. Leave the mobile app logged in. Do not copy `cookies.json` off the Mac.
2. On the cloud host, run `./scripts/start_mcp.sh` and `python3 scripts/health_check.py`. Confirm `health.ok` is true and `publishing_enabled` is false.
3. Run `python3 scripts/show_login_qr.py`. It writes `runtime/session/login-qr.png` (mode 600) and prints `timeout` plus `is_logged_in`. It does not print the image bytes.
4. Open that png on a trusted screen and scan it with the Xiaohongshu app for this account. The official server saves the session to `COOKIES_PATH`.
5. Run `python3 scripts/health_check.py --login-status`. Done means `is_logged_in: true` and `username_present: true`. The name itself is not printed.
6. Do not install crontab. Do not run the old publisher scripts except to see them exit 2.

If `/api/v1/login/qrcode` fails, the usual cause is the built-in browser missing system libraries (`libnss3`, `libatk`, `libgbm`, and the other Chromium shared libraries on that distro). Fix the host, then repeat from step 3. Still do not post.

## Later cadence (config and docs only)

Recorded in `config/config.json.example` under `cadence`. Not executed.

- At most 1 note per Asia/Shanghai calendar day.
- At least 24 hours after the previous note.
- Daytime only: 08:00 inclusive through 21:00 exclusive, UTC+8, no daylight-saving shift.
- A draft in `ready_to_publish` still does not auto-post.
- The retired clock was 08:00, 14:00, and 20:00 plus a random delay up to 60 minutes. Do not put it back.

`src/publish_guard.py` can answer whether a timestamp is inside that daytime window. `may_auto_post()` still returns false for those timestamps.

## What remains paused

- No cron, launchd, or scheduler entry is installed by this change.
- `src/xiaohongshu_random_publish.sh` and `src/xiaohongshu_post.sh` exit 2 immediately. They no longer sleep and they no longer call the publisher.
- `python3 src/xiaohongshu_pause.py resume` exits 2 and leaves publishing disabled.
- Comment checks and replies exit 2 and do not call the MCP.
