#!/usr/bin/env python3
"""
小红书发布暂停管理工具（本地使用）
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

PAUSE_FILE = Path.home() / ".xiaohongshu_pause.json"


def pause_for_days(days: int):
    """暂停指定天数"""
    resume_time = datetime.now() + timedelta(days=days)
    
    pause_info = {
        'paused': True,
        'paused_at': datetime.now().isoformat(),
        'resume_at': resume_time.isoformat(),
        'reason': f'用户手动暂停{days}天'
    }
    
    with open(PAUSE_FILE, 'w', encoding='utf-8') as f:
        json.dump(pause_info, f, ensure_ascii=False, indent=2)
    
    print(f"⏸️ 发布已暂停")
    print(f"   暂停时间: {pause_info['paused_at']}")
    print(f"   恢复时间: {pause_info['resume_at']}")
    print(f"   还有 {days} 天恢复")


def pause_until_date(date_str: str):
    """暂停到指定日期"""
    try:
        resume_time = datetime.strptime(date_str, '%Y-%m-%d')
        resume_time = resume_time.replace(hour=0, minute=0, second=0)
        
        if resume_time <= datetime.now():
            print(f"❌ 恢复时间必须在当前时间之后")
            return False
        
        pause_info = {
            'paused': True,
            'paused_at': datetime.now().isoformat(),
            'resume_at': resume_time.isoformat(),
            'reason': f'暂停到 {date_str}'
        }
        
        with open(PAUSE_FILE, 'w', encoding='utf-8') as f:
            json.dump(pause_info, f, ensure_ascii=False, indent=2)
        
        days = (resume_time - datetime.now()).days + 1
        print(f"⏸️ 发布已暂停")
        print(f"   暂停时间: {pause_info['paused_at']}")
        print(f"   恢复时间: {pause_info['resume_at']}")
        print(f"   大约 {days} 天后恢复")
        return True
        
    except ValueError:
        print(f"❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
        return False


def resume_publish():
    """恢复发布"""
    if PAUSE_FILE.exists():
        with open(PAUSE_FILE, 'r', encoding='utf-8') as f:
            pause_info = json.load(f)
        
        pause_info['paused'] = False
        pause_info['resumed_at'] = datetime.now().isoformat()
        
        with open(PAUSE_FILE, 'w', encoding='utf-8') as f:
            json.dump(pause_info, f, ensure_ascii=False, indent=2)
    
    print("▶️ 发布已恢复")


def check_status():
    """检查暂停状态"""
    if not PAUSE_FILE.exists():
        print("✅ 当前未暂停，发布正常进行")
        return True
    
    with open(PAUSE_FILE, 'r', encoding='utf-8') as f:
        pause_info = json.load(f)
    
    if not pause_info.get('paused', False):
        print("✅ 当前未暂停，发布正常进行")
        return True
    
    resume_at = datetime.fromisoformat(pause_info['resume_at'])
    
    if datetime.now() >= resume_at:
        # 暂停时间已过，自动恢复
        resume_publish()
        return True
    
    remaining = resume_at - datetime.now()
    days = remaining.days
    hours = remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60
    
    print(f"⏸️ 当前处于暂停状态")
    print(f"   暂停原因: {pause_info.get('reason', '未知')}")
    print(f"   暂停时间: {pause_info['paused_at']}")
    print(f"   恢复时间: {pause_info['resume_at']}")
    print(f"   剩余时间: {days}天 {hours}小时 {minutes}分钟")
    
    return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='小红书发布暂停管理')
    parser.add_argument('action', choices=['pause', 'resume', 'status', 'days', 'until'], 
                       help='操作')
    parser.add_argument('--days', '-d', type=int, default=2, help='暂停天数')
    parser.add_argument('--date', type=str, help='恢复日期 (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    if args.action == 'pause':
        pause_for_days(args.days)
    
    elif args.action == 'days':
        pause_for_days(args.days)
    
    elif args.action == 'until':
        if not args.date:
            print("❌ 请指定日期: --date 2024-03-20")
            sys.exit(1)
        pause_until_date(args.date)
    
    elif args.action == 'resume':
        resume_publish()
    
    elif args.action == 'status':
        check_status()


if __name__ == '__main__':
    main()
