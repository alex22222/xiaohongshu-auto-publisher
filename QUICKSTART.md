# 快速开始

发布保持关闭。下面只检查进程和登录状态，不发笔记。

细节在 [docs/cloud-architecture.md](docs/cloud-architecture.md) 和 [README.md](README.md)。GitHub `main` 可能比 Mac 上的 `/Users/henry/projects/xiaohongshu_auto` 旧，这次没有读取那份目录。

## 1. 安装 Python 依赖

```bash
python3 -m pip install -r requirements.txt
```

## 2. 在同一台云主机上编译并启动 MCP

源码是 [alex22222/xiaohongshu-mcp](https://github.com/alex22222/xiaohongshu-mcp) 的 `bb6fa2e208719ee634fec37881be29d3aa4699b3`（与上游 v2.7.4 同一提交；这个 fork 上没有名为 v2.7.4 的 tag）。需要 Go 1.27.3。两个 GitHub 仓库保持分开，不要把 MCP 源码提交进本仓库。

```bash
chmod +x scripts/*.sh scripts/*.py
./scripts/start_mcp.sh
```

进程只监听 `127.0.0.1:18060`。会话文件在 `runtime/session/cookies.json`，不要提交。第一次启动会编译 fork，并下载内置浏览器（约 150MB）。

## 3. 健康检查

```bash
python3 scripts/health_check.py
python3 scripts/health_check.py --login-status
```

第二条只打印是否已登录，不打印账号名、用户 ID 或 cookie。未扫码时 `is_logged_in` 应为 false。

## 4. 登录（需要所有者）

先停掉 Mac 上 `/Users/henry/projects/xiaohongshu-mcp` 的进程，并关掉 Cursor 里指向 `http://localhost:18060/mcp` 的 Mac 配置。不要拷贝 cookie 文件。

```bash
python3 scripts/show_login_qr.py
```

用小红书 App 扫描 `runtime/session/login-qr.png`，然后再跑一次 `--login-status`。扫码完成之前，登录保持未完成。

## 不要做的事

- 不要安装 crontab。旧的 8:00 / 14:00 / 20:00 任务曾经在约 26 分钟内发出 3 篇，必须继续暂停。
- 不要运行旧的发布脚本，它们会以退出码 2 拒绝。
- `python3 src/draft_pipeline.py publish` 也会拒绝。审过的草稿不会自动发。

以后的频率只写在配置里：每天最多 1 篇，间隔至少 24 小时，仅上海时区白天 08:00–21:00。当前不会按这个频率发帖。
