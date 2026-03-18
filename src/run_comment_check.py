#!/usr/bin/env python3
"""
小红书评论检查定时任务
每小时检查一次已发布笔记的新评论
"""

import sys
sys.path.insert(0, '/Users/henry')

from xiaohongshu_comment_reply_system import CommentReplySystem
from datetime import datetime
import argparse


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='小红书评论检查工具')
    parser.add_argument('--auto', action='store_true', 
                        help='自动回复模式（默认半自动）')
    parser.add_argument('--max-notes', type=int, default=5,
                        help='最多检查多少篇笔记（默认5）')
    parser.add_argument('--hours', type=int, default=72,
                        help='检查最近多少小时内的笔记（默认72）')
    parser.add_argument('--demo', action='store_true',
                        help='演示模式')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print(f"🤖 小红书评论检查任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    system = CommentReplySystem()
    
    if args.demo:
        # 演示模式：添加测试数据
        print("\n📝 演示模式：添加测试数据")
        test_note = {
            "feed_id": "test_note_001",
            "xsec_token": "test_token_001",
            "title": "甲状腺结节要不要手术？",
            "content": "体检发现甲状腺结节，大多数是良性的。建议每6-12个月复查一次超声。保持良好心态。",
            "image_path": "/Users/henry/Downloads/xiaohongshu_1.png",
            "published_at": datetime.now().isoformat(),
            "last_check": None,
            "total_comments": 0,
            "replied_count": 0
        }
        
        # 检查是否已存在
        exists = False
        for note in system.published_notes:
            if note.get("feed_id") == test_note["feed_id"]:
                exists = True
                break
        
        if not exists:
            system.published_notes.append(test_note)
            system._save_published_notes()
            print("✅ 已添加测试笔记")
        else:
            print("ℹ️ 测试笔记已存在")
        
        print("\n📋 已发布笔记列表:")
        for i, note in enumerate(system.published_notes[:5], 1):
            print(f"   {i}. {note.get('title', '无标题')[:40]}...")
            print(f"      发布于: {note.get('published_at', '未知')[:19]}")
        
        print("\n⚠️ 注意：演示模式下无法获取真实评论（需要真实的feed_id和xsec_token）")
        print("=" * 70)
        return
    
    # 正常执行检查
    stats = system.check_all_notes(
        auto_reply=args.auto,
        max_notes=args.max_notes,
        hours_ago=args.hours
    )
    
    if stats:
        print(f"\n✅ 任务完成！")
        print(f"   检查了 {stats.get('checked_notes', 0)} 篇笔记")
        print(f"   发现 {stats.get('new_comments', 0)} 条新评论")
        if args.auto:
            print(f"   自动回复了 {stats.get('replied_count', 0)} 条")
    else:
        print("\n⚠️ 本次检查没有符合条件的笔记")


if __name__ == "__main__":
    main()
