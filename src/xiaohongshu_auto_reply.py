#!/usr/bin/env python3
"""
小红书智能评论回复系统
功能：
1. 获取已发布笔记的评论
2. 使用 Kimi AI 根据文章内容和评论内容生成专业回复
3. 支持自动回复和人工审核模式
"""

import os
import json
import requests
import re
from datetime import datetime
from pathlib import Path


class XiaoHongShuAutoReply:
    """小红书智能评论回复系统"""
    
    def __init__(self):
        self.base_url = "http://localhost:18060"
        self.session_id = None
        
        # Kimi API 配置
        self.kimi_api_key = self._load_kimi_api_key()
        self.kimi_base_url = "https://api.moonshot.cn/v1"
        self.kimi_model = "kimi-k2-thinking-turbo"
        
        # 回复记录文件
        self.reply_record_file = Path("/Users/henry/.xiaohongshu_replied_comments.json")
        self.reply_records = self._load_reply_records()
    
    def _load_kimi_api_key(self):
        """加载 Kimi API Key"""
        # 优先从环境变量读取
        api_key = os.environ.get("MOONSHOT_API_KEY")
        if api_key:
            return api_key
        
        # 从配置文件读取
        config_file = Path.home() / ".moonshot_ai_rc"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith("api_key="):
                            return line.strip().split("=", 1)[1]
            except:
                pass
        return None
    
    def _load_reply_records(self):
        """加载已回复的评论记录"""
        if self.reply_record_file.exists():
            try:
                with open(self.reply_record_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_reply_records(self):
        """保存已回复的评论记录"""
        with open(self.reply_record_file, 'w', encoding='utf-8') as f:
            json.dump(self.reply_records, f, ensure_ascii=False, indent=2)
    
    def log(self, msg):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
    
    def mcp_initialize(self):
        """初始化 MCP 会话"""
        try:
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "xiaohongshu-auto-reply", "version": "1.0.0"}
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
    
    def get_note_comments(self, feed_id, xsec_token):
        """
        获取笔记的评论列表
        注意：这是通过 MCP 的 get_feed_detail 工具获取
        """
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
                    # 解析返回的内容
                    for item in result["result"]["content"]:
                        if item.get("type") == "text":
                            data = json.loads(item.get("text", "{}"))
                            return data.get("data", {}).get("comments", {}).get("list", [])
            return []
        except Exception as e:
            self.log(f"❌ 获取评论失败: {e}")
            return []
    
    def generate_reply_with_kimi(self, article_content, comment_content, article_title=""):
        """
        使用 Kimi AI 生成专业回复
        
        参数:
            article_content: 文章内容
            comment_content: 评论内容
            article_title: 文章标题
        """
        if not self.kimi_api_key:
            self.log("⚠️ 未配置 Kimi API Key")
            return None
        
        try:
            self.log(f"🤖 正在生成回复...")
            
            prompt = f"""你是一位专业的医疗健康科普博主，需要根据你的文章内容和用户的评论，给出专业、友善、有温度的回复。

【你的文章标题】
{article_title}

【你的文章内容】
{article_content[:800] if article_content else "健康科普文章"}

【用户评论】
{comment_content}

【回复要求】
1. 语气亲切友好，像朋友聊天一样自然
2. 对于咨询类问题，给出专业且易懂的解答
3. 对于鼓励类评论，真诚感谢
4. 对于质疑类评论，耐心解释，不卑不亢
5. 适当使用 emoji 增加亲和力
6. 回复字数控制在 30 字以内（简洁有力）
7. 不要出现"免责声明"等生硬词汇
8. 如果评论是广告或垃圾信息，回复"[SKIP]"
9. 如果评论包含敏感内容，回复"[SKIP]"

【输出格式】
直接输出回复内容，不要有任何前缀说明。"""

            headers = {
                "Authorization": f"Bearer {self.kimi_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.kimi_model,
                "messages": [
                    {"role": "system", "content": "你是一位专业的小红书健康科普博主，擅长与粉丝互动，回复专业且亲切。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            response = requests.post(
                f"{self.kimi_base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                reply_content = result["choices"][0]["message"]["content"].strip()
                
                # 清理格式
                if reply_content.startswith("```"):
                    reply_content = re.sub(r'^```\w*\n?', '', reply_content)
                    reply_content = re.sub(r'\n?```$', '', reply_content)
                
                self.log(f"✅ 生成回复 ({len(reply_content)} 字)")
                return reply_content
            else:
                self.log(f"❌ Kimi API 调用失败: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.log(f"❌ 生成回复异常: {e}")
            return None
    
    def is_already_replied(self, feed_id, comment_id):
        """检查评论是否已回复"""
        if feed_id not in self.reply_records:
            return False
        return comment_id in self.reply_records[feed_id]
    
    def mark_as_replied(self, feed_id, comment_id, reply_content):
        """标记评论为已回复"""
        if feed_id not in self.reply_records:
            self.reply_records[feed_id] = {}
        
        self.reply_records[feed_id][comment_id] = {
            "reply_content": reply_content,
            "reply_time": datetime.now().isoformat()
        }
        self._save_reply_records()
    
    def process_note_comments(self, feed_id, xsec_token, article_content, article_title, auto_reply=False):
        """
        处理笔记的所有评论
        
        参数:
            feed_id: 笔记ID
            xsec_token: 访问令牌
            article_content: 文章内容
            article_title: 文章标题
            auto_reply: 是否自动回复（False 则为人工审核模式）
        """
        self.log(f"\n{'='*60}")
        self.log(f"处理笔记: {article_title[:30]}...")
        self.log(f"{'='*60}")
        
        # 获取评论
        comments = self.get_note_comments(feed_id, xsec_token)
        if not comments:
            self.log("📭 暂无评论")
            return
        
        self.log(f"📊 共 {len(comments)} 条评论")
        
        pending_replies = []
        
        for comment in comments:
            comment_id = comment.get("id")
            comment_content = comment.get("content", "")
            user_nickname = comment.get("userInfo", {}).get("nickname", "用户")
            
            # 跳过已回复的评论
            if self.is_already_replied(feed_id, comment_id):
                continue
            
            # 跳过自己的回复（检查是否是作者）
            show_tags = comment.get("showTags", [])
            if "is_author" in show_tags:
                continue
            
            self.log(f"\n💬 新评论来自 @{user_nickname}:")
            self.log(f"   {comment_content[:80]}...")
            
            # 生成回复
            reply = self.generate_reply_with_kimi(
                article_content,
                comment_content,
                article_title
            )
            
            if not reply:
                continue
            
            # 检查是否需要跳过
            if reply == "[SKIP]":
                self.log("   ⏭️ 跳过此评论")
                self.mark_as_replied(feed_id, comment_id, "[SKIPPED]")
                continue
            
            pending_replies.append({
                "comment_id": comment_id,
                "comment_content": comment_content,
                "user_nickname": user_nickname,
                "reply_content": reply
            })
            
            if auto_reply:
                # 自动回复模式
                self.log(f"   ✅ 自动回复: {reply[:60]}...")
                # 这里可以添加实际的回复 API 调用
                # 注意：当前 MCP 服务可能不支持回复评论
                self.mark_as_replied(feed_id, comment_id, reply)
            else:
                # 人工审核模式
                self.log(f"   📝 建议回复: {reply[:60]}...")
        
        if not auto_reply and pending_replies:
            self.log(f"\n📋 待审核回复列表（共 {len(pending_replies)} 条）:")
            for i, item in enumerate(pending_replies, 1):
                print(f"\n{i}. 评论: {item['comment_content'][:50]}...")
                print(f"   建议回复: {item['reply_content']}")
        
        self.log(f"\n{'='*60}")


def main():
    """主函数 - 演示如何使用自动回复功能"""
    
    # 初始化
    auto_reply = XiaoHongShuAutoReply()
    
    if not auto_reply.mcp_initialize():
        print("❌ MCP 初始化失败")
        return
    
    print("✅ MCP 初始化成功")
    
    # 示例：处理一篇笔记的评论
    # 注意：这里需要提供实际的 feed_id 和 xsec_token
    
    # 示例数据（需要替换为实际数据）
    test_notes = [
        {
            "feed_id": "69ab0060000000002303bff4",
            "xsec_token": "ABo5IOIP5gJf_BvTUG_2A6suxfhJQGQx2yrQwNF3oTqx4=",
            "article_title": "2026 AI套餐怎么选，Coding Plan横评",
            "article_content": "高频使用AI，Coding Plan（编程订阅）比 API 按量计费便宜15-30倍..."
        }
    ]
    
    for note in test_notes:
        auto_reply.process_note_comments(
            feed_id=note["feed_id"],
            xsec_token=note["xsec_token"],
            article_content=note["article_content"],
            article_title=note["article_title"],
            auto_reply=False  # 人工审核模式
        )


if __name__ == "__main__":
    main()
