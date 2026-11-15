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
    """记录一次恢复请求，但保持发布关闭。"""
    pause_info = {
        'paused': True,
        'paused_at': datetime.now().isoformat(),
        'resume_at': None,
        'reason': 'cloud kill switch; resume does not enable posting',
    }
    if PAUSE_FILE.exists():
        try:
            with open(PAUSE_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                pause_info.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass
    pause_info['paused'] = True
    pause_info['resume_rejected_at'] = datetime.now().isoformat()
    pause_info['reason'] = 'cloud kill switch; resume does not enable posting'
    with open(PAUSE_FILE, 'w', encoding='utf-8') as f:
        json.dump(pause_info, f, ensure_ascii=False, indent=2)
    print(
        "Refused resume: publishing stays disabled. "
        "An approved draft does not auto-post.",
        file=sys.stderr,
    )
    raise SystemExit(2)


def check_status():
    """报告发布开关。到期的暂停文件不会自动恢复。"""
    print("publishing_enabled=false")
    print("auto_post=false")
    print("cron=paused")
    print("暂停到期也不会自动发笔记。resume 不能打开发布。")
    if not PAUSE_FILE.exists():
        return False
    try:
        with open(PAUSE_FILE, 'r', encoding='utf-8') as f:
            pause_info = json.load(f)
    except (OSError, json.JSONDecodeError):
        print("pause file unreadable")
        return False
    print(f"pause_file_paused={bool(pause_info.get('paused', False))}")
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
