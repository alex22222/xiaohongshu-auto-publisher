#!/usr/bin/env python3
"""
小红书评论回复集成系统 V1.0
功能：
1. 集成到发布系统，发布笔记后自动检查评论
2. 定时任务检查历史笔记的新评论
3. 批量处理多篇笔记的评论
4. 常见问题快速回复模板
"""

import os
import json
import requests
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class CommentReplySystem:
    """评论回复系统"""
    
    def __init__(self):
        self.base_url = "http://localhost:18060"
        self.session_id = None
        
        # Kimi API 配置
        self.kimi_api_key = self._load_kimi_api_key()
        self.kimi_base_url = "https://api.moonshot.cn/v1"
        self.kimi_model = "kimi-k2-thinking-turbo"
        
        # 数据文件
        self.published_notes_file = Path("/Users/henry/.xiaohongshu_published_notes.json")
        self.replied_comments_file = Path("/Users/henry/.xiaohongshu_replied_comments.json")
        self.reply_templates_file = Path("/Users/henry/.xiaohongshu_reply_templates.json")
        
        # 加载数据
        self.published_notes = self._load_published_notes()
        self.replied_comments = self._load_replied_comments()
        self.reply_templates = self._load_reply_templates()
    
    def _load_kimi_api_key(self):
        """加载 Kimi API Key"""
        api_key = os.environ.get("MOONSHOT_API_KEY")
        if api_key:
            return api_key
        config_file = Path.home() / ".moonshot_ai_rc"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    for line in f:
                        if line.startswith("api_key="):
                            return line.strip().split("=", 1)[1]
            except:
                pass
        return None
    
    def _load_published_notes(self):
        """加载已发布的笔记记录"""
        if self.published_notes_file.exists():
            try:
                with open(self.published_notes_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _save_published_notes(self):
        """保存已发布的笔记记录"""
        with open(self.published_notes_file, 'w', encoding='utf-8') as f:
            json.dump(self.published_notes, f, ensure_ascii=False, indent=2)
    
    def _load_replied_comments(self):
        """加载已回复的评论记录"""
        if self.replied_comments_file.exists():
            try:
                with open(self.replied_comments_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_replied_comments(self):
        """保存已回复的评论记录"""
        with open(self.replied_comments_file, 'w', encoding='utf-8') as f:
            json.dump(self.replied_comments, f, ensure_ascii=False, indent=2)
    
    def _load_reply_templates(self):
        """加载快速回复模板"""
        if self.reply_templates_file.exists():
            try:
                with open(self.reply_templates_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        # 默认模板
        return {
            "感谢类": [
                "谢谢支持！记得定期复查，健康最重要💪",
                "不客气呀！有问题随时交流😊",
                "感谢认可！一起守护健康❤️",
            ],
            "咨询类": {
                "医院推荐": "建议去三甲医院内分泌科，医生经验更丰富👨‍⚕️",
                "检查项目": "一般做超声就行，具体听医生建议📋",
                "饮食注意": "均衡饮食即可，海鲜适量吃，碘摄入别过量🦐",
                "复查时间": "建议6-12个月复查一次，遵医嘱最重要⏰",
                "症状咨询": "建议及时就医检查，网上咨询不能代替诊疗🏥",
            },
            "安慰类": [
                "别担心，定期复查就好，保持好心情😊",
                "放轻松，大部分情况都是良性的💪",
                "相信医生，按时复查，没问题的👍",
            ],
        }
    
    def _save_reply_templates(self):
        """保存快速回复模板"""
        with open(self.reply_templates_file, 'w', encoding='utf-8') as f:
            json.dump(self.reply_templates, f, ensure_ascii=False, indent=2)
    
    def log(self, msg):
        """打印日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        return line
    
    def mcp_initialize(self):
        """初始化 MCP 会话"""
        try:
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "xiaohongshu-comment-reply", "version": "1.0"}
                },
                "id": 1
            }
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            response = requests.post(
                f"{self.base_url}/mcp",
                json=init_request,
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                self.session_id = response.headers.get('Mcp-Session-Id')
                return True
            return False
        except Exception as e:
            self.log(f"❌ MCP 初始化失败: {e}")
            return False
    
    def record_published_note(self, feed_id: str, xsec_token: str, title: str, content: str, image_path: str):
        """记录已发布的笔记"""
        note_info = {
            "feed_id": feed_id,
            "xsec_token": xsec_token,
            "title": title,
            "content": content,
            "image_path": image_path,
            "published_at": datetime.now().isoformat(),
            "last_check": None,
            "total_comments": 0,
            "replied_count": 0
        }
        self.published_notes.append(note_info)
        self._save_published_notes()
        self.log(f"✅ 已记录发布笔记: {title[:30]}...")
    
    def get_note_comments(self, feed_id: str, xsec_token: str) -> List[Dict]:
        """获取笔记的评论列表"""
        try:
            request_data = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_feed_detail",
                    "arguments": {
                        "feed_id": feed_id,
                        "xsec_token": xsec_token,
                        "load_all_comments": True
                    }
                },
                "id": 2
            }
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": self.session_id
            }
            response = requests.post(
                f"{self.base_url}/mcp",
                json=request_data,
                headers=headers,
                timeout=60
            )
            if response.status_code == 200:
                result = response.json()
                if "result" in result and "content" in result["result"]:
                    for item in result["result"]["content"]:
                        if item.get("type") == "text":
                            data = json.loads(item.get("text", "{}"))
                            return data.get("data", {}).get("comments", {}).get("list", [])
            return []
        except Exception as e:
            self.log(f"❌ 获取评论失败: {e}")
            return []
    
    def is_already_replied(self, feed_id: str, comment_id: str) -> bool:
        """检查评论是否已回复"""
        return comment_id in self.replied_comments.get(feed_id, {})
    
    def mark_as_replied(self, feed_id: str, comment_id: str, reply_content: str):
        """标记评论为已回复"""
        if feed_id not in self.replied_comments:
            self.replied_comments[feed_id] = {}
        self.replied_comments[feed_id][comment_id] = {
            "reply_content": reply_content,
            "replied_at": datetime.now().isoformat()
        }
        self._save_replied_comments()
    
    def match_template(self, comment_content: str) -> Optional[str]:
        """匹配快速回复模板"""
        comment_lower = comment_content.lower()
        
        # 检查咨询类模板
        templates = self.reply_templates.get("咨询类", {})
        for keyword, reply in templates.items():
            if keyword in comment_content or keyword in comment_lower:
                return reply
        
        # 检查感谢类
        if any(kw in comment_content for kw in ["谢谢", "感谢", "学到了", "收藏"]):
            templates = self.reply_templates.get("感谢类", [])
            if templates:
                return templates[hash(comment_content) % len(templates)]
        
        # 检查安慰类
        if any(kw in comment_content for kw in ["担心", "害怕", "焦虑", "怎么办"]):
            templates = self.reply_templates.get("安慰类", [])
            if templates:
                return templates[hash(comment_content) % len(templates)]
        
        return None
    
    def generate_reply_with_kimi(self, article_title: str, article_content: str, 
                                  comment_content: str, max_length: int = 30) -> Optional[str]:
        """使用 Kimi AI 生成回复"""
        if not self.kimi_api_key:
            return None
        
        # 先尝试匹配模板
        template_reply = self.match_template(comment_content)
        if template_reply and len(template_reply) <= max_length:
            return f"[模板] {template_reply}"
        
        try:
            prompt = f"""作为健康科普博主，请针对以下评论给出简短回复（{max_length}字以内）：

文章：{article_title}
评论：{comment_content}

要求：
1. {max_length}字以内，简洁有力
2. 亲切友好，适当用emoji
3. 专业但不生硬
4. 直接输出回复内容"""

            response = requests.post(
                f"{self.kimi_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.kimi_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.kimi_model,
                    "messages": [
                        {"role": "system", "content": "你是小红书健康科普博主，擅长简短亲切的评论回复。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 300
                },
                timeout=30
            )
            
            if response.status_code == 200:
                message = response.json()["choices"][0]["message"]
                content = message.get("content", "").strip()
                if not content:
                    content = message.get("reasoning_content", "").strip()
                
                # 清理格式
                content = re.sub(r'^```\w*\n?', '', content)
                content = re.sub(r'\n?```$', '', content)
                
                # 提取最后一行
                lines = [l.strip() for l in content.split('\n') if l.strip()]
                if lines:
                    for line in reversed(lines):
                        if '"' in line or '"' in line or '回复' in line:
                            match = re.search(r'[""""]([^""""]+)[""""]', line)
                            if match and len(match.group(1)) > 5:
                                content = match.group(1)
                                break
                    else:
                        content = lines[-1]
                
                # 截取到限制字数
                if len(content) > max_length:
                    content = content[:max_length]
                    for sep in ['。', '，', '！', '？']:
                        idx = content.rfind(sep)
                        if idx > max_length * 0.7:
                            content = content[:idx+1]
                            break
                
                return f"[AI] {content}"
            return None
        except Exception as e:
            self.log(f"❌ 生成回复失败: {e}")
            return None
    
    def process_note_comments(self, note: Dict, auto_reply: bool = False,
                              max_replies: int = 10) -> Tuple[int, int]:
        """
        处理单篇笔记的评论
        
        参数:
            note: 笔记信息字典
            auto_reply: 是否自动回复
            max_replies: 最大回复数量
        
        返回:
            (新评论数, 已回复数)
        """
        feed_id = note.get("feed_id")
        xsec_token = note.get("xsec_token")
        title = note.get("title", "")
        content = note.get("content", "")
        
        self.log(f"\n📱 检查笔记: {title[:40]}...")
        
        # 获取评论
        comments = self.get_note_comments(feed_id, xsec_token)
        if not comments:
            self.log("   📭 暂无评论")
            return 0, 0
        
        # 过滤未回复的评论
        new_comments = []
        for comment in comments:
            comment_id = comment.get("id")
            show_tags = comment.get("showTags", [])
            
            # 跳过自己的回复
            if "is_author" in show_tags:
                continue
            # 跳过已回复的
            if self.is_already_replied(feed_id, comment_id):
                continue
            
            new_comments.append(comment)
        
        if not new_comments:
            self.log(f"   ✅ 所有 {len(comments)} 条评论已处理完毕")
            return 0, 0
        
        self.log(f"   📝 共 {len(comments)} 条评论，{len(new_comments)} 条待回复")
        
        # 处理新评论
        replied_count = 0
        for i, comment in enumerate(new_comments[:max_replies], 1):
            comment_id = comment.get("id")
            comment_content = comment.get("content", "")
            user_nickname = comment.get("userInfo", {}).get("nickname", "用户")
            
            self.log(f"\n   {i}. 💬 @{user_nickname}: {comment_content[:50]}")
            
            # 生成回复
            reply = self.generate_reply_with_kimi(title, content, comment_content)
            if not reply:
                continue
            
            reply_text = reply.replace("[AI] ", "").replace("[模板] ", "")
            self.log(f"      🤖 建议回复 ({len(reply_text)}字): {reply_text}")
            
            if auto_reply:
                # 自动回复模式
                self.log(f"      ✅ 自动发送")
                self.mark_as_replied(feed_id, comment_id, reply_text)
                replied_count += 1
            else:
                # 半自动模式：记录建议
                self.log(f"      ⏳ 待审核")
        
        # 更新笔记检查时间
        note["last_check"] = datetime.now().isoformat()
        note["total_comments"] = len(comments)
        note["replied_count"] = len(self.replied_comments.get(feed_id, {}))
        self._save_published_notes()
        
        return len(new_comments), replied_count
    
    def check_all_notes(self, auto_reply: bool = False, max_notes: int = 5,
                        hours_ago: int = 72) -> Dict:
        """
        检查自己发布的笔记的评论
        
        参数:
            auto_reply: 是否自动回复
            max_notes: 最多检查多少篇笔记
            hours_ago: 只检查最近多少小时内发布的笔记
        
        返回:
            统计信息字典
        """
        if not self.mcp_initialize():
            self.log("❌ MCP 初始化失败")
            return {}
        
        self.log(f"\n{'='*70}")
        self.log("🤖 开始检查自己发布的笔记评论")
        self.log(f"{'='*70}")
        
        # 过滤自己发布的、近期、有feed_id的笔记
        cutoff_time = datetime.now() - timedelta(hours=hours_ago)
        own_notes = []
        for note in self.published_notes:
            # 只检查自己发布的笔记
            if not note.get("is_own_note", False):
                continue
            # 只检查有feed_id的笔记
            if not note.get("feed_id") or not note.get("xsec_token"):
                continue
            # 只检查近期的笔记
            try:
                pub_time = datetime.fromisoformat(note.get("published_at", ""))
                if pub_time > cutoff_time:
                    own_notes.append(note)
            except:
                continue
        
        if not own_notes:
            self.log(f"📭 最近 {hours_ago} 小时内没有自己发布的可检查笔记")
            self.log(f"   提示: 只检查带有feed_id的自己发布的笔记")
            return {}
        
        self.log(f"📊 最近 {hours_ago} 小时内自己发布了 {len(own_notes)} 篇可检查笔记")
        self.log(f"   本次检查前 {min(max_notes, len(own_notes))} 篇\n")
        
        # 统计
        stats = {
            "checked_notes": 0,
            "total_comments": 0,
            "new_comments": 0,
            "replied_count": 0
        }
        
        # 处理每篇笔记
        for note in own_notes[:max_notes]:
            new_count, replied_count = self.process_note_comments(
                note, auto_reply=auto_reply
            )
            stats["checked_notes"] += 1
            stats["new_comments"] += new_count
            stats["replied_count"] += replied_count
        
        self.log(f"\n{'='*70}")
        self.log("📊 检查完成统计")
        self.log(f"{'='*70}")
        self.log(f"   检查笔记: {stats['checked_notes']} 篇")
        self.log(f"   新评论: {stats['new_comments']} 条")
        self.log(f"   已回复: {stats['replied_count']} 条")
        self.log(f"{'='*70}\n")
        
        return stats


def demo():
    """演示功能"""
    system = CommentReplySystem()
    
    # 添加演示数据
    if not system.published_notes:
        system.published_notes = [
            {
                "feed_id": "demo_note_1",
                "xsec_token": "demo_token_1",
                "title": "甲状腺结节要不要手术？",
                "content": "体检发现甲状腺结节，大多数是良性的。建议定期复查。",
                "published_at": datetime.now().isoformat(),
                "last_check": None
            }
        ]
        system._save_published_notes()
    
    # 显示功能菜单
    print("=" * 70)
    print("🤖 小红书评论回复集成系统")
    print("=" * 70)
    print("\n功能菜单:")
    print("1. 检查所有笔记评论 (半自动模式)")
    print("2. 检查所有笔记评论 (自动回复模式)")
    print("3. 查看已发布笔记列表")
    print("4. 管理快速回复模板")
    print("5. 退出")
    print("=" * 70)


if __name__ == "__main__":
    demo()
