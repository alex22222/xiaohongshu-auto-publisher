#!/usr/bin/env python3
"""
小红书发布器 - 直接调用mcp服务
"""

import json
import urllib.request
import urllib.error
from pathlib import Path

def publish_content(title, content, images, tags):
    """
    调用xiaohongshu-mcp服务发布内容
    """
    # mcp服务地址
    mcp_url = "http://localhost:18060/mcp"
    
    # 构建请求
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "publish_content",
            "arguments": {
                "title": title,
                "content": content,
                "images": images if isinstance(images, list) else [images],
                "tags": tags if isinstance(tags, list) else tags.split(",")
            }
        },
        "id": 1
    }
    
    try:
        # 发送请求
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            mcp_url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if 'result' in result:
                return True, result['result']
            elif 'error' in result:
                return False, result['error']
            else:
                return True, result
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return False, f"HTTP错误 {e.code}: {error_body}"
    except Exception as e:
        return False, str(e)

def check_mcp_service():
    """检查mcp服务是否运行"""
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:18060/mcp", method='OPTIONS')
        with urllib.request.urlopen(req, timeout=5) as response:
            return True
    except:
        return False

def start_mcp_service():
    """启动mcp服务"""
    import subprocess
    import time
    
    mcp_path = "/Users/henry/xiaohongshu-mcp/xiaohongshu-mcp-darwin-amd64"
    
    # 检查是否已经在运行
    if check_mcp_service():
        print("mcp服务已在运行")
        return True
    
    # 启动服务
    try:
        print("正在启动mcp服务...")
        process = subprocess.Popen(
            [mcp_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd="/Users/henry/xiaohongshu-mcp"
        )
        
        # 等待服务启动
        for i in range(10):
            time.sleep(1)
            if check_mcp_service():
                print("mcp服务启动成功")
                return True
        
        print("mcp服务启动超时")
        return False
        
    except Exception as e:
        print(f"启动mcp服务失败: {e}")
        return False

def main():
    """测试发布"""
    # 检查/启动服务
    if not start_mcp_service():
        print("无法启动mcp服务")
        return
    
    # 测试发布
    result = publish_content(
        title="测试发布",
        content="这是一条测试内容",
        images=["/Users/henry/Downloads/xiaohongshu_1_babeichong.png"],
        tags=["测试", "健康"]
    )
    
    print(f"发布结果: {result}")

if __name__ == "__main__":
    main()
