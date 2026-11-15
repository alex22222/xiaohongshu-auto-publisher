# 小红书自动发布系统

**Publishing is paused.** This checkout does not post notes, does not resume cron, and does not send comments or likes. The owner is the only person who may click Publish, and that action is not wired. A ready draft does not auto-post.

GitHub `main` may be behind the Mac tree at `/Users/henry/projects/xiaohongshu_auto`. That directory was not read for this change. The Mac MCP at `/Users/henry/projects/xiaohongshu-mcp` (`http://localhost:18060/mcp` in Cursor) is no longer the runtime. Architecture: [docs/cloud-architecture.md](docs/cloud-architecture.md).

Official server: [xiaohongshu-mcp v2.7.4](https://github.com/xpzouying/xiaohongshu-mcp/releases/tag/v2.7.4) (2026-11-10), Linux binary `xiaohongshu-mcp-linux-amd64`, loopback `127.0.0.1:18060`.

## Run a health check (no posting)

On the cloud host, Linux x64, from this repo:

```bash
python3 -m pip install -r requirements.txt
chmod +x scripts/*.sh scripts/*.py
./scripts/start_mcp.sh
python3 scripts/health_check.py
python3 scripts/health_check.py --login-status
```

`health_check.py` calls `GET /health`. With `--login-status` it also calls `GET /api/v1/login/status` and prints only `is_logged_in` and `username_present`. It does not print cookies, tokens, account ids, or the raw body.

Stop the process with `./scripts/stop_mcp.sh`. The first start downloads the upstream built-in browser (about 150MB) into `runtime/session/`, which is gitignored.

Local pause state, which does not contact Xiaohongshu:

```bash
python3 src/xiaohongshu_pause.py status
```

`publishing_enabled=false` and `auto_post=false` are the expected lines. `resume` exits 2 and does not enable posting.

## What the owner still has to do

Login is blocked until these steps happen on the durable cloud host. They were not completed in the environment that prepared this change.

1. Stop the Mac process under `/Users/henry/projects/xiaohongshu-mcp`, and disable the Mac Cursor `mcp.json` entry for `http://localhost:18060/mcp`. One account cannot stay on two web logins. Do not copy `cookies.json` into git, chat, or this host.
2. `./scripts/start_mcp.sh`, then `python3 scripts/health_check.py`. Confirm `health.ok` is true.
3. `python3 scripts/show_login_qr.py`. This writes `runtime/session/login-qr.png` and prints a timeout. Scan that image with the Xiaohongshu app. Do not commit the png.
4. `python3 scripts/health_check.py --login-status`. Login is done when `is_logged_in` is true. The script still will not post.
5. Leave cron uninstalled. The old 08:00 / 14:00 / 20:00 jobs, plus a random delay, once posted 3 notes in about 26 minutes.

If the QR request fails, the host is usually missing Chromium libraries (`libnss3`, `libatk`, `libgbm`, and the rest of the distro's Chromium dependency set). Install those, then repeat the QR step. Still do not post.

Optional `AUTH_TOKEN` is read from the environment by the official binary. Leave it unset while the server is bound to `127.0.0.1`. Never commit the value. See `.env.example`.

## Drafts

Local files only, under gitignored `runtime/drafts/`:

```bash
python3 src/draft_pipeline.py init --title "标题" --body "正文"
python3 src/draft_pipeline.py review --id <id>
python3 src/draft_pipeline.py ready --id <id>
python3 src/draft_pipeline.py publish --id <id>   # exits 2
```

`ready` does not post. `publish` does not call the MCP.

## Later cadence (not active)

`config/config.json.example` records the limit for a future change. Nothing enforces it by posting.

- At most 1 note per day.
- At least 24 hours between notes.
- Daytime only, Asia/Shanghai 08:00 inclusive to 21:00 exclusive.

An approved draft still does not auto-post. `schedule.enabled` is false and `schedule.cron` is null. Do not install crontab.

## Old scripts

These exit 2 before any Xiaohongshu write or comment call:

- `src/xiaohongshu_full_auto_system_v3_complete.py`
- `src/xiaohongshu_publisher.py`
- `src/xiaohongshu_auto_scheduler.py`
- `src/xiaohongshu_auto_post.py`
- `src/xiaohongshu_post.sh`
- `src/xiaohongshu_random_publish.sh`
- `src/xiaohongshu_auto_reply.py`
- `src/xiaohongshu_comment_reply_system.py`
- `src/run_comment_check.py`

They still contain the previous Mac paths and generators. Those paths are leftover from GitHub `main`, not instructions.

## Layout

```
scripts/start_mcp.sh          official v2.7.4 process on 127.0.0.1:18060
scripts/health_check.py       GET /health and optional login status
scripts/show_login_qr.py      owner QR, written to runtime/session/
src/publish_guard.py          kill switch (no allow branch)
src/draft_pipeline.py         draft -> review -> ready; publish refused
src/mcp_health.py             redacted health and login summaries
config/config.json.example    publishing off, cadence documented only
config/mcp-v2.7.4.sha256      official binary checksums
runtime/                      binary, session, logs (gitignored)
docs/cloud-architecture.md    process, port, session, wiring
```

## Checks

```bash
python3 -m pytest tests -q
python3 -m py_compile src/*.py scripts/*.py
```

## License

MIT. This tool is for the account owner. Follow Xiaohongshu's rules. Do not commit `runtime/`, `cookies.json`, `.env`, or QR images.
