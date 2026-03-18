# 小红书自动发布系统

🤖 基于Python的小红书自动化内容发布系统，支持定时发布、智能内容生成和评论自动回复。

## ✨ 功能特性

- 📅 **定时发布**: 支持每天定时（8:00、14:00、20:00）自动发布内容
- 📝 **智能内容**: 从Excel数据源自动读取文章，生成小红书风格内容
- 🖼️ **自动配图**: 自动匹配文章配图，支持多数据源
- 💬 **评论回复**: 自动监控评论并智能回复
- 🔄 **防重复**: 自动记录已发布内容，避免重复发布
- ⏸️ **暂停功能**: 支持临时暂停发布，到期自动恢复
- 📊 **发布记录**: 完整的发布历史记录和统计

## 🚀 快速开始

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

### 3. 配置MCP工具

```bash
# 下载MCP工具到 mcp/ 目录
# 从Release页面下载对应系统版本
chmod +x mcp/xiaohongshu-mcp-*

# 登录小红书
./mcp/xiaohongshu-login-darwin-amd64
# 按提示扫码登录
```

### 4. 配置数据源

编辑 `config/config.json`：

```json
{
  "data_sources": {
    "ruijin": {
      "name": "瑞金医院",
      "file": "/path/to/ruijin_articles.xlsx",
      "image_prefix": "xiaohongshu_",
      "image_dir": "/path/to/images"
    }
  }
}
```

### 5. 运行测试

```bash
python3 src/xiaohongshu_full_auto_system_v3_complete.py
```

### 6. 设置定时任务

```bash
crontab -e

# 添加以下行（每天8:00、14:00、20:00发布）
0 8,14,20 * * * cd /path/to/xiaohongshu-auto-publisher && python3 src/xiaohongshu_full_auto_system_v3_complete.py >> logs/publisher.log 2>&1
```

## 📁 项目结构

```
xiaohongshu-auto-publisher/
├── src/                          # 源代码
│   ├── xiaohongshu_full_auto_system_v3_complete.py  # 主程序
│   ├── xiaohongshu_auto_scheduler.py               # 调度器
│   ├── xiaohongshu_auto_reply.py                   # 自动回复
│   └── ...
├── mcp/                          # MCP工具（需单独下载）
│   ├── xiaohongshu-mcp-*
│   └── cookies.json
├── config/                       # 配置文件
│   ├── config.json.example       # 配置模板
│   └── config.json               # 实际配置（gitignore）
├── data/                         # 数据文件
│   ├── used_records.json         # 已使用记录
│   └── publish_history.json      # 发布历史
├── logs/                         # 日志文件
├── docs/                         # 文档
│   ├── 安装指南.md
│   ├── 使用说明.md
│   └── 迁移指南.md
├── requirements.txt              # Python依赖
└── README.md                     # 本文件
```

## 📝 配置说明

### 环境变量

创建 `.env` 文件：

```bash
# MCP配置
MCP_PORT=18060
MCP_API_KEY=your-secret-key

# 时区
TZ=Asia/Shanghai

# 可选：通知配置
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
```

### Excel数据源格式

| 序号 | 文章标题 | 文章链接 | 分类 | 配图路径 |
|------|----------|----------|------|----------|
| 1 | 甲状腺结节的治疗 | http://... | 甲状腺健康 | xiaohongshu_1_jiazhuangxian.png |
| 2 | 肝癌早期筛查 | http://... | 肿瘤防治 | zhongliu_2_ganai.png |

## 🛠️ 核心脚本说明

| 脚本 | 功能 |
|------|------|
| `xiaohongshu_full_auto_system_v3_complete.py` | 完整版自动发布系统 ⭐推荐 |
| `xiaohongshu_auto_scheduler.py` | 定时任务调度器 |
| `xiaohongshu_auto_reply.py` | 评论自动回复 |
| `xiaohongshu_comment_reply_system.py` | 评论监控系统 |
| `xiaohongshu_pause.py` | 暂停/恢复发布管理 |

## 🔧 常用命令

```bash
# 立即发布一次
python3 src/xiaohongshu_full_auto_system_v3_complete.py

# 暂停发布2天
python3 src/xiaohongshu_pause.py days --days 2

# 恢复发布
python3 src/xiaohongshu_pause.py resume

# 查看状态
python3 src/xiaohongshu_pause.py status

# 检查评论
python3 src/run_comment_check.py
```

## ⚠️ 注意事项

1. **Cookie有效期**: 小红书登录状态通常保持30天，过期需重新登录
2. **发布频率**: 建议每天不超过3条，避免触发风控
3. **内容规范**: 确保发布内容符合小红书社区规范
4. **隐私安全**: 不要将 `cookies.json` 和配置文件提交到GitHub

## 🔒 安全提示

- 已将敏感配置文件加入 `.gitignore`
- 使用 `config.json.example` 作为配置模板
- 定期备份 `data/` 目录下的使用记录

## 📝 更新日志

### v3.0 (2026-03)
- 新增完整版发布系统
- 支持Kimi AI生成内容
- 优化暂停功能

### v2.0 (2026-02)
- 新增评论自动回复
- 支持多数据源

### v1.0 (2026-01)
- 基础发布功能
- 定时任务支持

## 🤝 贡献指南

欢迎提交Issue和PR！

## 📄 许可证

MIT License

## 💡 免责声明

本工具仅供学习和研究使用，请遵守小红书平台规则和相关法律法规。使用本工具产生的任何后果由使用者自行承担。

---

**⭐ 如果这个项目对你有帮助，请给个Star！**
