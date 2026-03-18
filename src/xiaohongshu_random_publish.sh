#!/bin/bash
# 小红书随机时间发布脚本
# 在指定时段内随机延迟后执行发布

# 生成0-3600秒（0-60分钟）的随机延迟
DELAY=$((RANDOM % 3600))

# 记录日志
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 将在 ${DELAY} 秒 ($(expr $DELAY / 60) 分 $(expr $DELAY % 60) 秒) 后执行发布" >> /Users/henry/xiaohongshu_random_schedule.log

# 随机延迟
sleep $DELAY

# 执行发布
cd /Users/henry
/usr/local/bin/python3 /Users/henry/xiaohongshu_full_auto_system_v3_complete.py >> /Users/henry/xiaohongshu_auto_system_v3_complete.log 2>&1

# 记录完成日志
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 发布执行完成" >> /Users/henry/xiaohongshu_random_schedule.log
