#!/bin/bash
# 小红书自动发布脚本
# 每天定时执行

echo "=================================="
echo "小红书自动发布任务"
echo "时间: $(date)"
echo "=================================="

# 执行Python脚本获取发布信息
python3 /Users/henry/xiaohongshu_auto_post.py

# 检查是否有发布信息
INFO_FILE="/Users/henry/.xiaohongshu_post_info.json"
if [ ! -f "$INFO_FILE" ]; then
    echo "没有生成发布信息，退出"
    exit 1
fi

# 读取发布信息
TITLE=$(python3 -c "import json; print(json.load(open('$INFO_FILE'))['title'])")
CONTENT=$(python3 -c "import json; print(json.load(open('$INFO_FILE'))['content'])")
IMAGE=$(python3 -c "import json; print(json.load(open('$INFO_FILE'))['image'])")
TAGS=$(python3 -c "import json; print(','.join(json.load(open('$INFO_FILE'))['tags']))")
RECORD_ID=$(python3 -c "import json; print(json.load(open('$INFO_FILE'))['record_id'])")
SOURCE=$(python3 -c "import json; print(json.load(open('$INFO_FILE'))['source'])")

echo ""
echo "准备发布:"
echo "标题: $TITLE"
echo "图片: $IMAGE"
echo "记录ID: $RECORD_ID"

# 调用Python脚本使用mcp工具发布
cat > /tmp/do_publish.py << 'PYEOF'
import sys
import json

# 读取发布信息
with open("/Users/henry/.xiaohongshu_post_info.json", "r", encoding="utf-8") as f:
    info = json.load(f)

title = info["title"]
content = info["content"]
image = info["image"]
tags = info["tags"]

# 构建发布参数
print(f"发布标题: {title}")
print(f"发布图片: {image}")
print(f"标签: {tags}")
PYEOF

python3 /tmp/do_publish.py

# 由于无法直接在shell中调用mcp工具，这里输出指令供手动执行或后续开发
echo ""
echo "=================================="
echo "请使用以下信息手动发布到小红书:"
echo "=================================="
echo "标题: $TITLE"
echo "图片路径: $IMAGE"
echo "标签: $TAGS"
echo ""

# 记录成功发布（假设发布成功）
# 实际使用时，应该在确认发布成功后执行此操作
python3 << EOF
import json

used_file = "/Users/henry/.xiaohongshu_used_records.json"
record_id = "$RECORD_ID"
source = "$SOURCE"

try:
    with open(used_file, "r", encoding="utf-8") as f:
        data = json.load(f)
except:
    data = {"ruijin": [], "zhongliu": []}

if record_id not in data.get(source, []):
    data[source].append(record_id)
    with open(used_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 已记录发布: {record_id}")
else:
    print(f"记录已存在: {record_id}")
EOF

echo "=================================="
echo "任务完成"
echo "=================================="
