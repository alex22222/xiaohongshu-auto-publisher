# 快速开始

## 5分钟快速上手

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/xiaohongshu-auto-publisher.git
cd xiaohongshu-auto-publisher
```

### 2. 安装依赖

```bash
# macOS
brew install python3 ffmpeg
pip3 install -r requirements.txt

# Linux
sudo apt-get install python3 ffmpeg
pip3 install -r requirements.txt
```

### 3. 下载MCP工具

访问 [Release页面](https://github.com/yourusername/xiaohongshu-auto-publisher/releases) 下载对应系统的MCP工具，解压到 `mcp/` 目录。

```bash
chmod +x mcp/xiaohongshu-mcp-*
./mcp/xiaohongshu-login-darwin-amd64
```

### 4. 配置

```bash
cp config/config.json.example config/config.json
# 编辑 config.json，填写你的Excel路径和图片路径
```

### 5. 运行

```bash
python3 src/xiaohongshu_full_auto_system_v3_complete.py
```

## 下一步

- 阅读 [安装指南](docs/安装指南.md) 获取详细安装说明
- 阅读 [使用说明](docs/使用说明.md) 了解高级功能
- 设置定时任务实现自动发布

## 需要帮助？

- 查看 [README.md](README.md)
- 提交 [Issue](https://github.com/yourusername/xiaohongshu-auto-publisher/issues)
