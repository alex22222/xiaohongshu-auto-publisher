#!/usr/bin/env python3
"""小红书发布器。

云端客户端只连接本机 127.0.0.1:18060 上的官方 MCP。
发布调用会拒绝，不再启动 Mac 上的二进制。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_guard


def publish_content(title, content, images, tags):
    """拒绝发布。参数保留给旧调用方，不会发到网络上。"""
    del title, content, images, tags
    publish_guard.refuse("publish_content")


def check_mcp_service():
    """进程是否在监听，由 scripts/health_check.py 检查。这里不发请求。"""
    print(f"mcp_base_url={publish_guard.mcp_base_url()}")
    print("use scripts/health_check.py")
    return False


def start_mcp_service():
    """不在这里启动进程，避免再拉起 Mac 二进制。"""
    print("Use scripts/start_mcp.sh for official v2.7.4 on 127.0.0.1:18060.", file=sys.stderr)
    return False


def main():
    publish_guard.refuse("xiaohongshu_publisher")


if __name__ == "__main__":
    main()
