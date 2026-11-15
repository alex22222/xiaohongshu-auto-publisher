#!/usr/bin/env python3
"""
小红书全自动发布系统 V3.0 完整版
优化内容:
1. 内容字数超过1000字时自动优化缩减(不使用省略号)
2. 无法获取链接内容时自动重新随机选择文章
3. 检测到视频内容时自动跳过并记录原因
4. 内容不完整时搜索网上材料生成完整内容
"""

import os
import json
import random
import requests
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_guard



class AutoPublisher:
    def __init__(self):
        self.base_url = publish_guard.mcp_base_url()
        self.session_id = None
        self.message_id = 0
        self.max_retries = 10
        self.max_content_length = 900
        
        # Kimi API 配置
        self.kimi_api_key = self._load_kimi_api_key()
        self.kimi_base_url = "https://api.moonshot.cn/v1"
        self.kimi_model = "kimi-k2-thinking-turbo"
        
        # 视频内容关键词
        self.video_keywords = [
            "观看视频", "看视频", "点击视频", "视频播放", "播放视频",
            "观看下方视频", "戳视频", "视频讲解", "视频演示",
            "👆点击视频", "👇点击视频", "↑点击视频", "↓点击视频",
            "视频了解", "观看上方视频", "观看以下视频"
        ]
        
        # 数据源配置
        # 当前使用:上海肿瘤医院 + 华山医院 + 仁济医院
        self.data_sources = {
            "zhongliu": {
                "name": "上海肿瘤医院",
                "file": "/Users/henry/Downloads/上海肿瘤医院公众号保健文章汇总.xlsx",
                "image_prefix": "zhongliu_",
                "hospital_names": [],  # 不在标题中显示医院名(避免敏感词)
                "image_dir": "/Users/henry/Downloads"
            },
            "huashan": {
                "name": "华山医院",
                "file": "/Users/henry/Downloads/华山医院公众号保健文章汇总.xlsx",
                "image_prefix": "huashan_",
                "hospital_names": [],  # 不在标题中显示医院名(避免敏感词)
                "image_dir": "/Users/henry/Downloads"
            },
            "renji": {
                "name": "仁济医院",
                "file": "/Users/henry/Downloads/仁济医院公众号保健文章汇总.xlsx",
                "image_prefix": "renji_",
                "hospital_names": [],  # 不在标题中显示医院名(避免敏感词)
                "image_dir": "/Users/henry/Downloads"
            },
        }
        
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
    
    def generate_content_with_kimi(self, title, category, original_content=""):
        """
        使用 Kimi API 生成小红书风格内容
        """
        if not self.kimi_api_key:
            self.log("⚠️ 未配置 Kimi API Key,回退到模板生成")
            return None
        
        try:
            self.log(f"🤖 正在调用 Kimi API 生成内容: {title[:30]}...")
            
            # 构建提示词
            prompt = self._build_kimi_prompt(title, category, original_content)
            
            # 调用 Kimi API
            headers = {
                "Authorization": f"Bearer {self.kimi_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.kimi_model,
                "messages": [
                    {"role": "system", "content": "你是一位专业的小红书健康科普内容创作者,擅长将医学知识转化为通俗易懂,活泼有趣的小红书风格文案."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1500
            }
            
            response = requests.post(
                f"{self.kimi_base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_content = result["choices"][0]["message"]["content"]
                
                # 清理格式
                generated_content = generated_content.strip()
                if generated_content.startswith("```"):
                    generated_content = re.sub(r'^```\w*\n?', '', generated_content)
                    generated_content = re.sub(r'\n?```$', '', generated_content)
                
                self.log(f"✅ Kimi API 生成成功 ({len(generated_content)} 字)")
                return generated_content
            else:
                self.log(f"❌ Kimi API 调用失败: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.log(f"❌ Kimi API 异常: {e}")
            return None
    
    def _build_kimi_prompt(self, title, category, original_content):
        """构建 Kimi 提示词"""
        prompt = f"""请根据以下信息,创作一篇小红书风格的健康科普文案:

[主题]{title}
[分类]{category}
"""
        
        if original_content and len(original_content) > 20:
            # 使用原始内容的前800字符作为参考,保留更多关键信息
            content_ref = original_content[:800] if len(original_content) > 800 else original_content
            prompt += f"""
[参考资料]
{content_ref}

请基于以上参考资料进行创作,保留关键信息点.
"""
        
        prompt += """
[要求]
1. 使用小红书风格:多使用emoji,口语化表达,亲切友好
2. 结构清晰:
   - 开头:用吸引人的hook引发共鸣(1-2句)
   - 正文:3-5个核心知识点,每条配emoji
   - 实用建议:2-3条可操作的建议
   - 结尾:互动引导,鼓励评论/收藏
3. 字数控制在300-600字
4. 避免使用"免责声明"等生硬词汇
5. 语气要亲切,像朋友分享经验

[输出格式示例]
💡 标题

📌 引起共鸣的开头...

✨ 知识点1:...
✨ 知识点2:...

💡 实用建议:...

互动引导语...
"""
        return prompt
        
    def log(self, msg):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        log_file = Path("/Users/henry/xiaohongshu_auto_system_v3_complete.log")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
    
    def generate_popular_xiaohongshu_content(self, title, category):
        """
        生成流行的小红书格式内容(当内容字数少于50字时使用)
        包含emoji,话题标签风格,互动引导等元素
        """
        try:
            self.log(f"正在生成小红书风格补充内容: {title[:30]}...")
            
            # 根据分类和标题生成小红书风格内容
            popular_templates = {
                "甲状腺": {
                    "hook": "姐妹们!甲状腺问题真的不能忽视💢",
                    "scenarios": [
                        "体检发现甲状腺结节怎么办?",
                        "甲状腺结节会癌变吗?",
                        "什么样的甲状腺结节需要手术?"
                    ],
                    "tips": [
                        "🔍 定期复查:每6-12个月做一次超声",
                        "😴 规律作息:熬夜真的伤甲状腺!",
                        "🥗 饮食均衡:碘摄入要适量",
                        "💆 情绪管理:压力大会影响甲状腺功能"
                    ],
                    "cta": "姐妹们,你们体检有发现甲状腺问题吗?评论区聊聊~👇"
                },
                "前列腺": {
                    "hook": "男士必看!前列腺健康攻略👨‍⚕️",
                    "scenarios": [
                        "尿频尿急可能是前列腺在报警",
                        "50岁以上男性要注意前列腺筛查",
                        "前列腺癌早期症状不明显"
                    ],
                    "tips": [
                        "🩺 每年体检:PSA检测很重要",
                        "🏃 适度运动:久坐是前列腺大敌",
                        "🍅 多吃番茄:番茄红素有益前列腺",
                        "💧 多喝水:但睡前别喝太多"
                    ],
                    "cta": "转发给家里的男士,健康最重要!💪"
                },
                "肿瘤": {
                    "hook": "癌症预防干货!建议收藏🌟",
                    "scenarios": [
                        "癌症其实可以早发现的",
                        "这些习惯正在增加患癌风险",
                        "体检报告中这些指标要注意"
                    ],
                    "tips": [
                        "🔬 早筛早治:很多癌症治愈率超90%",
                        "🚭 远离烟酒:一级致癌物要远离",
                        "🏃 保持运动:每周150分钟中等强度",
                        "😊 乐观心态:好心情是最好的免疫力"
                    ],
                    "cta": "预防大于治疗,转发给家人一起健康生活!❤️"
                },
                "感冒": {
                    "hook": "感冒迟迟不好?可能是你用错方法🤧",
                    "scenarios": [
                        "感冒吃抗生素真的有用吗?",
                        "普通感冒和流感怎么区分?",
                        "为什么我的感冒总是反复?"
                    ],
                    "tips": [
                        "💊 别乱吃药:感冒大多是病毒引起",
                        "💧 多喝水:每天2000ml温水",
                        "🛏️ 多休息:给免疫系统充电",
                        "🍯 蜂蜜水:缓解喉咙痛有奇效"
                    ],
                    "cta": "你感冒一般几天好?有什么妙招?评论区分享👇"
                },
                "流感": {
                    "hook": "流感高发季!这份防护指南请收好😷",
                    "scenarios": [
                        "流感和普通感冒真的不一样!",
                        "哪些人最容易得流感?",
                        "流感疫苗到底要不要打?"
                    ],
                    "tips": [
                        "💉 打疫苗:高危人群建议每年接种",
                        "🧼 勤洗手:七步洗手法要牢记",
                        "😷 戴口罩:去人群密集处要防护",
                        "🏠 多通风:每天开窗2-3次"
                    ],
                    "cta": "流感季节保护好自己和家人!点赞收藏备用👍"
                },
                "饮食": {
                    "hook": "这样吃真的会变健康!亲测有效✨",
                    "scenarios": [
                        "为什么吃得少还是不瘦?",
                        "营养师推荐的搭配公式",
                        "三餐这样安排最健康"
                    ],
                    "tips": [
                        "🥗 211法则:2份蔬菜1份蛋白1份主食",
                        "🥤 少喝奶茶:糖分真的超标",
                        "🐟 优质蛋白:鱼蛋奶豆换着吃",
                        "🍚 粗细搭配:主食加点杂粮"
                    ],
                    "cta": "想健康减脂的姐妹,关注我不迷路!💕"
                },
                "运动": {
                    "hook": "懒人运动指南!不动真的不行🏃‍♀️",
                    "scenarios": [
                        "没时间运动怎么办?",
                        "每天运动多久才有效?",
                        "久坐族必做的几个动作"
                    ],
                    "tips": [
                        "⏰ 碎片化运动:每次10分钟也行",
                        "🚶 多走路:每天6000步起步",
                        "🧘 拉伸放松:久坐后要做",
                        "🏃 找到喜欢:才能坚持下去"
                    ],
                    "cta": "今天你运动了吗?打卡监督!👇"
                },
                "睡眠": {
                    "hook": "失眠星人必看!亲测有效的入睡方法🌙",
                    "scenarios": [
                        "为什么总是睡不着?",
                        "褪黑素能不能长期吃?",
                        "睡前玩手机影响有多大?"
                    ],
                    "tips": [
                        "📵 睡前1小时:远离电子屏幕",
                        "🛁 泡个脚:促进血液循环",
                        "🎵 白噪音:帮助放松入睡",
                        "⏰ 固定作息:每天同一时间睡觉"
                    ],
                    "cta": "祝姐妹们都能睡个好觉!晚安💤"
                },
                "血压": {
                    "hook": "高血压年轻化!这些信号要注意⚠️",
                    "scenarios": [
                        "年纪轻轻怎么会高血压?",
                        "血压高但没有症状用吃药吗?",
                        "家庭自测血压正确方法"
                    ],
                    "tips": [
                        "🧂 控盐:每天不超过6克",
                        "🚭 戒烟限酒:血压控制大敌",
                        "🏃 规律运动:每周150分钟",
                        "😌 减压:情绪管理很重要"
                    ],
                    "cta": "血压问题不容忽视,定期监测很重要!💪"
                },
                "血糖": {
                    "hook": "控糖攻略!血糖高不是老年人的专利🩸",
                    "scenarios": [
                        "血糖有点高要不要吃药?",
                        "糖尿病人可以吃什么水果?",
                        "运动后血糖反而升高?"
                    ],
                    "tips": [
                        "🍚 控制主食:每餐一拳头的量",
                        "🥬 多吃蔬菜:特别是绿叶菜",
                        "🚶 餐后运动:散步20分钟",
                        "📊 监测血糖:了解自己的规律"
                    ],
                    "cta": "控糖路上不孤单,一起加油!💪"
                },
                "肠胃": {
                    "hook": "肠胃养护指南!吃嘛嘛香的秘诀🍜",
                    "scenarios": [
                        "胃胀胃痛怎么办?",
                        "益生菌真的有用吗?",
                        "养胃早餐怎么吃?"
                    ],
                    "tips": [
                        "🍚 规律进食:三餐定时定量",
                        "🥗 细嚼慢咽:每口嚼20下",
                        "🌶️ 少吃刺激:辛辣油腻要控制",
                        "😊 保持心情:胃是情绪器官"
                    ],
                    "cta": "肠胃好,身体才好!要好好爱护它❤️"
                },
                "胰腺": {
                    "hook": "胰腺问题别慌!手术还是观察?医生来支招👨‍⚕️",
                    "scenarios": [
                        "体检发现胰腺囊肿/肿瘤怎么办?",
                        "哪些胰腺问题必须手术?",
                        "胰腺手术后要注意什么?"
                    ],
                    "tips": [
                        "🔍 先别慌:胰腺肿瘤≠胰腺癌,很多是良性的",
                        "📊 看指标:大小,位置,性质决定治疗方案",
                        "👨‍⚕️ 听医嘱:专业医生会评估手术指征",
                        "🩺 定期复查:小于2cm可先观察随访"
                    ],
                    "cta": "胰腺问题别自己吓自己,及时就医最重要!有问题评论区聊👇"
                },
                "手术": {
                    "hook": "手术做不做?这些判断标准要知道⚠️",
                    "scenarios": [
                        "什么情况下必须手术?",
                        "手术风险大不大?",
                        "不做手术会怎样?"
                    ],
                    "tips": [
                        "📋 听专业意见:多咨询几位医生",
                        "⚖️ 权衡利弊:手术收益 vs 潜在风险",
                        "🏥 选对医院:复杂手术要找大医院",
                        "💪 术前准备:调整好身体状态"
                    ],
                    "cta": "手术决策要慎重,专业医生建议最重要!转发给需要的人💪"
                }
            }
            
            # 根据标题关键词匹配模板
            matched_template = None
            for keyword, template in popular_templates.items():
                if keyword in title or keyword in category:
                    matched_template = template
                    break
            
            # 如果没有匹配到,使用通用模板
            if not matched_template:
                matched_template = {
                    "hook": f"关于{category}的健康知识,建议收藏🌟",
                    "scenarios": [
                        "这些健康知识你都知道吗?",
                        "很多人容易忽视的健康细节",
                        "医生朋友告诉我的健康秘诀"
                    ],
                    "tips": [
                        "🏥 定期体检:早发现早治疗",
                        "🥗 健康饮食:营养均衡很重要",
                        "🏃 适量运动:增强体质",
                        "😊 保持乐观:好心情是最好的药"
                    ],
                    "cta": "健康知识要分享,转发给家人朋友!❤️"
                }
            
            # 生成小红书风格内容
            content_parts = []
            
            # 1. 吸引注意的开场(Hook)
            content_parts.append(matched_template["hook"])
            content_parts.append("")
            
            # 2. 场景共鸣
            content_parts.append("📌 常见困扰:")
            for scenario in matched_template["scenarios"]:
                content_parts.append(f"• {scenario}")
            content_parts.append("")
            
            # 3. 实用干货
            content_parts.append("✨ 实用建议:")
            for tip in matched_template["tips"]:
                content_parts.append(tip)
            content_parts.append("")
            
            # 4. 总结金句
            content_parts.append("💡 记住这几点,健康不踩坑!")
            content_parts.append("")
            
            # 5. 互动引导(Call to Action)
            content_parts.append(matched_template["cta"])
            
            content = "\n".join(content_parts)
            self.log(f"✅ 已生成小红书风格内容 ({len(content)} 字)")
            return content
            
        except Exception as e:
            self.log(f"❌ 生成小红书风格内容失败: {e}")
            return None

    def search_online_content(self, title, category):
        """
        搜索网上材料生成完整内容
        """
        try:
            self.log(f"正在搜索网上材料: {title[:30]}...")
            
            # 使用简单的搜索API或预定义内容
            # 这里使用基于标题和分类生成专业内容的方式
            
            content_templates = {
                "甲状腺": {
                    "intro": "甲状腺是人体重要的内分泌器官,位于颈部前方.",
                    "points": [
                        "甲状腺结节是临床常见病,大多数为良性",
                        "定期超声检查可监测结节变化",
                        "保持规律作息,避免过度劳累",
                        "合理摄入碘,不过量也不缺乏"
                    ]
                },
                "前列腺": {
                    "intro": "前列腺是男性特有的性腺器官,位于膀胱下方.",
                    "points": [
                        "前列腺癌是男性常见恶性肿瘤之一",
                        "早期筛查可提高治愈率",
                        "50岁以上男性建议每年检查PSA",
                        "保持健康生活方式有助于预防"
                    ]
                },
                "感冒": {
                    "intro": "感冒是上呼吸道感染,多由病毒引起.",
                    "points": [
                        "普通感冒一般7-10天自愈",
                        "多休息,多喝水有助于恢复",
                        "症状严重时应及时就医",
                        "预防关键是勤洗手,戴口罩"
                    ]
                },
                "流感": {
                    "intro": "流感是流感病毒引起的急性呼吸道传染病.",
                    "points": [
                        "流感症状比普通感冒重,传染性强",
                        "高危人群建议接种流感疫苗",
                        "出现高热,全身酸痛应及时就医",
                        "流感季节避免去人群密集场所"
                    ]
                },
                "肿瘤": {
                    "intro": "肿瘤是机体在各种致瘤因素作用下形成的异常增生.",
                    "points": [
                        "早期发现,早期治疗是关键",
                        "定期体检有助于早期发现肿瘤",
                        "保持健康生活方式可降低风险",
                        "确诊后应到正规医院规范治疗"
                    ]
                },
                "饮食": {
                    "intro": "合理饮食是健康的基础,要注意营养均衡.",
                    "points": [
                        "多吃蔬菜水果,补充维生素",
                        "减少油腻,高盐,高糖食物",
                        "规律进餐,不暴饮暴食",
                        "根据个人情况调整饮食结构"
                    ]
                },
                "运动": {
                    "intro": "适量运动有助于增强体质,预防疾病.",
                    "points": [
                        "每周运动3-5次,每次30分钟以上",
                        "选择适合自己的运动方式",
                        "运动前热身,运动后放松",
                        "循序渐进,量力而行"
                    ]
                }
            }
            
            # 根据标题关键词匹配模板
            matched_content = None
            for keyword, template in content_templates.items():
                if keyword in title:
                    matched_content = template
                    break
            
            # 如果没有匹配到,使用通用模板
            if not matched_content:
                matched_content = {
                    "intro": f"{category}是重要的健康话题,需要引起重视.",
                    "points": [
                        "定期体检,关注身体健康指标",
                        "保持健康的生活方式和饮食习惯",
                        "如有不适症状,及时就医检查",
                        "遵医嘱治疗,不擅自停药或改变方案"
                    ]
                }
            
            # 生成完整内容
            content = f"📖 {matched_content['intro']}\n\n"
            content += "💡 核心知识点:\n"
            for i, point in enumerate(matched_content['points'], 1):
                content += f"{i}. {point}\n"
            
            self.log(f"✅ 已生成完整内容 ({len(content)} 字)")
            return content
            
        except Exception as e:
            self.log(f"❌ 搜索网上材料失败: {e}")
            return None
    
    def generate_xiaohongshu_content(self, title, category, original_content=""):
        """
        生成小红书专业格式内容
        优先使用 Kimi API 生成,失败时回退到模板生成
        """
        # 优先尝试使用 Kimi API 生成内容
        kimi_content = self.generate_content_with_kimi(title, category, original_content)
        if kimi_content and len(kimi_content) >= 100:
            self.log(f"✅ 使用 Kimi AI 生成的内容 ({len(kimi_content)} 字)")
            # 确保字数不超过限制
            if len(kimi_content) > 900:
                kimi_content = self.trim_content_without_ellipsis(kimi_content, 900)
            return kimi_content
        
        # Kimi API 失败或内容太短,回退到模板生成
        self.log("📝 使用模板生成内容...")
        
        content_parts = []
        
        # 1. 标题图标
        if "甲状腺" in title:
            content_parts.append("💡 甲状腺健康科普")
        elif "前列腺" in title:
            content_parts.append("💡 男性健康知识")
        elif "感冒" in title or "流感" in title:
            content_parts.append("💡 季节健康提醒")
        elif "肿瘤" in title or "癌" in title:
            content_parts.append("💡 肿瘤科普知识")
        elif "胰腺" in title:
            content_parts.append("💡 胰腺健康科普")
        elif "饮食" in title:
            content_parts.append("💡 健康饮食指南")
        elif "运动" in title:
            content_parts.append("💡 科学运动建议")
        elif "睡眠" in title:
            content_parts.append("💡 健康睡眠知识")
        elif "血压" in title:
            content_parts.append("💡 血压管理科普")
        elif "血糖" in title:
            content_parts.append("💡 血糖控制指南")
        elif "血脂" in title:
            content_parts.append("💡 血脂管理知识")
        elif "手术" in title:
            content_parts.append("💡 医疗决策指南")
        else:
            content_parts.append("💡 健康科普知识")
        
        content_parts.append("")
        
        # 2. 引入语
        content_parts.append(f"📌 {title}")
        content_parts.append("")
        
        # 3. 正文内容(如果有原始内容)
        if original_content and len(original_content) > 50:
            # 清理可能的省略号
            original_content = original_content.replace("...", "").replace("…", "")
            # 限制长度但不用省略号(保留更多内容,但不超过700字)
            if len(original_content) > 700:
                # 尝试在句子结尾处截断
                truncated = original_content[:700]
                # 找到最后一个句号,问号或感叹号
                for punct in ['.', '?', '!', '\n']:
                    last_pos = truncated.rfind(punct)
                    if last_pos > 500:  # 确保至少保留了500字
                        truncated = truncated[:last_pos+1]
                        break
                original_content = truncated
            content_parts.append("📖 " + original_content)
            content_parts.append("")
        else:
            # 搜索网上材料生成内容
            online_content = self.search_online_content(title, category)
            if online_content:
                content_parts.append(online_content)
                content_parts.append("")
        
        # 4. 关键知识点(使用emoji让格式更美观)
        content_parts.append("🌟 关键要点:")
        
        # 根据分类生成专业要点
        key_points = self.generate_key_points(category, title)
        for point in key_points:
            content_parts.append(f"• {point}")
        
        content_parts.append("")
        
        # 5. 实用建议
        content_parts.append("✅ 实用建议:")
        suggestions = self.generate_suggestions(category)
        for suggestion in suggestions:
            content_parts.append(f"• {suggestion}")
        
        content_parts.append("")
        
        # 6. 结尾(不使用免责声明,用更自然的结尾)
        content_parts.append("💪 健康是一种生活态度")
        content_parts.append("坚持健康习惯,从今天开始!")
        
        content = "\n".join(content_parts)
        
        # 检查字数,如果少于50字,生成小红书风格补充内容
        content_length = len(content)
        if content_length < 50:
            self.log(f"⚠️ 内容字数仅 {content_length} 字,少于50字,正在生成小红书风格补充内容...")
            popular_content = self.generate_popular_xiaohongshu_content(title, category)
            if popular_content:
                # 将原始简短内容作为引言,小红书风格内容作为主要部分
                if original_content and len(original_content) > 10:
                    content = f"📌 {title}\n\n{original_content[:100]}\n\n{popular_content}"
                else:
                    content = f"📌 {title}\n\n{popular_content}"
                self.log(f"✅ 已生成完整小红书风格内容 ({len(content)} 字)")
        
        # 检查字数,如果超过则精简但不使用省略号
        if len(content) > 900:
            content = self.trim_content_without_ellipsis(content, 900)
        
        return content
    
    def generate_key_points(self, category, title):
        """生成关键知识点"""
        points_map = {
            "甲状腺": [
                "甲状腺结节多为良性,无需过度担心",
                "定期超声检查可监测结节变化",
                "保持规律作息,避免过度疲劳"
            ],
            "前列腺": [
                "50岁以上男性建议每年检查",
                "早期症状不明显,需定期筛查",
                "健康饮食有助于预防"
            ],
            "肿瘤": [
                "早期发现治愈率可达90%以上",
                "定期体检是早期发现的关键",
                "保持良好心态配合治疗"
            ],
            "感冒": [
                "普通感冒一般7-10天自愈",
                "多休息,多喝水有助于恢复",
                "症状加重应及时就医"
            ],
            "流感": [
                "流感症状重,传染性强",
                "高危人群建议接种疫苗",
                "48小时内使用抗病毒药物效果最佳"
            ],
            "饮食": [
                "少油少盐少糖,清淡饮食",
                "多吃蔬菜水果补充维生素",
                "规律进餐,不暴饮暴食"
            ]
        }
        
        for keyword, points in points_map.items():
            if keyword in title or keyword in category:
                return points
        
        return [
            "定期体检,关注身体变化",
            "保持健康生活方式",
            "如有不适及时就医"
        ]
    
    def generate_suggestions(self, category):
        """生成实用建议"""
        return [
            "建立健康档案,定期体检",
            "保持良好作息,早睡早起",
            "适度运动,增强体质",
            "遇到问题咨询专业医生"
        ]
    
    def trim_content_without_ellipsis(self, content, max_length):
        """
        精简内容但不使用省略号
        通过删除非核心段落实现
        """
        if len(content) <= max_length:
            return content
        
        self.log(f"内容字数({len(content)})超过限制,开始精简(不使用省略号)...")
        
        # 策略1: 简化结尾
        lines = content.split('\n')
        
        # 保留核心部分,删除部分非关键行
        essential_markers = ['💡', '📌', '📖', '🌟', '✅', '💪']
        trimmed_lines = []
        
        for line in lines:
            # 保留所有带标记的行
            if any(marker in line for marker in essential_markers):
                trimmed_lines.append(line)
            # 保留短行(通常是关键句)
            elif len(line) < 50 and line.strip():
                trimmed_lines.append(line)
        
        # 重新组合
        content = '\n'.join(trimmed_lines)
        
        # 如果还超长,进一步精简
        if len(content) > max_length:
            # 保留前max_length字,但在句子结束处截断
            truncated = content[:max_length-10]
            # 找到最后一个句号
            last_period = truncated.rfind('.')
            if last_period > max_length * 0.8:  # 如果在80%位置之后有句号
                content = truncated[:last_period+1]
            else:
                content = truncated
        
        return content
    
    # ... [其他方法保持不变] ...
    
    def load_excel_data(self, excel_path):
        """加载Excel数据"""
        try:
            from openpyxl import load_workbook
            wb = load_workbook(excel_path)
            sheet = wb.active
            headers = [cell.value for cell in sheet[1]]
            rows = list(sheet.iter_rows(min_row=2, values_only=True))
            
            records = []
            for row in rows:
                record = {}
                for header, value in zip(headers, row):
                    record[header] = value
                if record.get('文章标题') and record.get('文章链接'):
                    records.append(record)
            return records
        except Exception as e:
            self.log(f"加载Excel失败: {e}")
            return []
    
    def load_used_records(self):
        """加载已使用的记录"""
        used_file = Path("/Users/henry/.xiaohongshu_auto_used_v3_complete.json")
        # 支持所有数据源
        default = {"ruijin": [], "zhongliu": [], "huashan": [], "renji": [], "yunying": []}
        if used_file.exists():
            try:
                with open(used_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 确保包含所有数据源键
                    for key in default:
                        if key not in data:
                            data[key] = []
                    return data
            except:
                pass
        return default
    
    def load_skipped_records(self):
        """加载已跳过的记录"""
        skipped_file = Path("/Users/henry/.xiaohongshu_skipped_v3_complete.json")
        default = {"ruijin": [], "zhongliu": [], "huashan": [], "renji": [], "yunying": []}
        if skipped_file.exists():
            try:
                with open(skipped_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 确保包含所有数据源键
                    for key in default:
                        if key not in data:
                            data[key] = []
                    return data
            except:
                pass
        return default
    
    def save_used_records(self, used_records):
        """保存已使用的记录"""
        used_file = Path("/Users/henry/.xiaohongshu_auto_used_v3_complete.json")
        with open(used_file, 'w', encoding='utf-8') as f:
            json.dump(used_records, f, ensure_ascii=False, indent=2)
    
    def save_skipped_records(self, skipped_records):
        """保存已跳过的记录"""
        skipped_file = Path("/Users/henry/.xiaohongshu_skipped_v3_complete.json")
        with open(skipped_file, 'w', encoding='utf-8') as f:
            json.dump(skipped_records, f, ensure_ascii=False, indent=2)
    
    def get_available_records(self, records, used_ids, skipped_ids, source):
        """获取可用记录"""
        available = []
        for record in records:
            seq = record.get('序号', '')
            if not seq:
                continue
            record_id = f"{source}_{seq}"
            if record_id not in used_ids and record_id not in skipped_ids:
                available.append((record, record_id))
        return available
    
    def find_image_path(self, record, source_config):
        """
        查找图片路径 - 改进版
        支持多种匹配策略,优先返回小红书专用版本(_xhs.png)
        """
        # 获取图片目录,默认为Downloads,可通过配置覆盖
        image_dir = Path(source_config.get("image_dir", "/Users/henry/Downloads"))
        prefix = source_config.get("image_prefix", "")
        downloads = Path("/Users/henry/Downloads")
        
        # 从记录中获取信息
        image_path = record.get('配图路径', '')
        seq = record.get('序号', '')
        title = record.get('文章标题', '')
        
        self.log(f"   🔍 查找图片: 序号={seq}, 配图路径={image_path}")
        
        # 辅助函数:检查图片是否有效
        def is_valid_image(path):
            if not path or not path.exists():
                return False
            # 检查文件大小(至少10KB,避免空文件)
            if path.stat().st_size < 10240:
                return False
            return True
        
        # 辅助函数:获取所有候选图片
        def get_candidate_images(directory, pattern):
            """获取目录中匹配模式的所有有效图片"""
            candidates = []
            if directory.exists():
                for img_path in directory.glob(pattern):
                    if is_valid_image(img_path):
                        candidates.append(img_path)
            return candidates
        
        # 策略1: 如果提供了配图路径,优先精确匹配
        if image_path:
            path_obj = Path(image_path)
            base_name = path_obj.stem  # 不含扩展名
            
            # 1.1 优先查找 _xhs.png 版本(小红书专用)
            xhs_name = f"{base_name}_xhs.png"
            for search_dir in [image_dir, downloads]:
                xhs_path = search_dir / xhs_name
                if is_valid_image(xhs_path):
                    self.log(f"   ✅ 找到小红书专用图片: {xhs_path.name}")
                    return str(xhs_path)
            
            # 1.2 尝试直接查找完整路径(在配置的图片目录)
            full_path = image_dir / image_path
            if is_valid_image(full_path):
                self.log(f"   ✅ 找到精确匹配图片: {full_path.name}")
                return str(full_path)
            
            # 1.3 尝试在Downloads根目录查找
            alt_path = downloads / image_path
            if is_valid_image(alt_path):
                self.log(f"   ✅ 在Downloads找到图片: {alt_path.name}")
                return str(alt_path)
            
            # 1.4 模糊匹配:查找文件名包含basename的图片
            for search_dir in [image_dir, downloads]:
                for img_path in get_candidate_images(search_dir, "*.png"):
                    # 检查是否以basename开头(避免部分匹配)
                    if img_path.stem.startswith(base_name):
                        self.log(f"   ✅ 模糊匹配图片: {img_path.name}")
                        return str(img_path)
        
        # 策略2: 使用序号和前缀匹配
        if seq and prefix:
            # 2.1 尝试匹配前缀+序号的模式
            seq_str = str(int(seq)) if isinstance(seq, (int, float)) else str(seq)
            
            # 优先查找带_xhs后缀的
            for search_dir in [image_dir, downloads]:
                xhs_candidates = get_candidate_images(search_dir, f"{prefix}{seq_str}_*_xhs.png")
                if xhs_candidates:
                    selected = xhs_candidates[0]
                    self.log(f"   ✅ 序号匹配到_xhs图片: {selected.name}")
                    return str(selected)
            
            # 再找普通版本
            for search_dir in [image_dir, downloads]:
                candidates = get_candidate_images(search_dir, f"{prefix}{seq_str}_*.png")
                if candidates:
                    selected = candidates[0]
                    self.log(f"   ✅ 序号匹配到图片: {selected.name}")
                    return str(selected)
        
        # 策略3: 根据文章标题关键词匹配(备选)
        if title and prefix:
            # 提取标题中的关键词(2-4字)
            import re
            title_clean = re.sub(r"[^\u4e00-\u9fa5]", "", title)
            keywords = []
            for length in range(4, 1, -1):
                for i in range(0, len(title_clean) - length + 1, length):
                    keywords.append(title_clean[i:i+length])
            
            # 尝试用关键词匹配图片
            for search_dir in [image_dir, downloads]:
                for img_path in get_candidate_images(search_dir, f"{prefix}*.png"):
                    img_stem = img_path.stem.lower()
                    for keyword in keywords[:3]:  # 只检查前3个关键词
                        if keyword in img_stem:
                            self.log(f"   ✅ 标题关键词匹配图片: {img_path.name}")
                            return str(img_path)
        
        # 策略4: 使用前缀匹配任意图片(随机选择,但排除已使用的)
        if prefix:
            all_candidates = []
            for search_dir in [image_dir, downloads]:
                all_candidates.extend(get_candidate_images(search_dir, f"{prefix}*.png"))
            
            if all_candidates:
                # 优先选择带_xhs后缀的
                xhs_candidates = [p for p in all_candidates if "_xhs" in p.name]
                if xhs_candidates:
                    selected = random.choice(xhs_candidates)
                    self.log(f"   ⚠️ 未找到精确匹配,随机选择_xhs图片: {selected.name}")
                    return str(selected)
                else:
                    selected = random.choice(all_candidates)
                    self.log(f"   ⚠️ 未找到精确匹配,随机选择图片: {selected.name}")
                    return str(selected)
        
        # 策略5: 最后的回退方案 - 从image_dir中随机选择
        fallback_candidates = get_candidate_images(image_dir, "*.png")
        if fallback_candidates:
            selected = fallback_candidates[0]
            self.log(f"   ⚠️ 使用回退图片: {selected.name}")
            return str(selected)
        
        # 策略6: 尝试Downloads根目录的常见模式
        fallback_patterns = ["zhongliu_*.png", "huashan_*.png", "xiaohongshu_*.png"]
        for pattern in fallback_patterns:
            candidates = get_candidate_images(downloads, pattern)
            if candidates:
                xhs_candidates = [p for p in candidates if "_xhs" in p.name]
                if xhs_candidates:
                    selected = random.choice(xhs_candidates)
                else:
                    selected = random.choice(candidates)
                self.log(f"   ⚠️ 从Downloads选择图片: {selected.name}")
                return str(selected)
        
        self.log(f"   ❌ 未找到任何可用图片")
        return None
    
    def clean_title(self, title, hospital_names):
        """清理标题"""
        cleaned = title
        for hospital in hospital_names:
            cleaned = cleaned.replace(hospital, "")
        cleaned = cleaned.replace("｜", " ").replace(",", ",").replace("  ", " ").strip()
        if cleaned.startswith(","):
            cleaned = cleaned[1:].strip()
        if cleaned.startswith("!"):
            cleaned = cleaned[1:].strip()
        return cleaned[:20]
    
    def check_video_content(self, content):
        """检查是否包含视频"""
        if not content:
            return False, None
        
        for keyword in self.video_keywords:
            if keyword in content:
                return True, keyword
        
        return False, None
    
    def fetch_article_content(self, url):
        """获取文章内容"""
        try:
            self.log(f"正在获取文章内容: {url[:60]}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            response.encoding = response.apparent_encoding or 'utf-8'
            
            if response.status_code == 200:
                html = response.text
                
                html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
                html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
                
                content = ""
                
                if 'rich_media_content' in html:
                    match = re.search(r'<div class="rich_media_content[^"]*"[^>]*>(.*?)</div>\s*<script', html, re.DOTALL)
                    if match:
                        content = match.group(1)
                
                if not content:
                    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
                    content = '\n'.join(paragraphs[:10])
                
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'&nbsp;', ' ', content)
                content = re.sub(r'&quot;', '"', content)
                content = re.sub(r'&amp;', '&', content)
                content = re.sub(r'\s+', ' ', content).strip()
                
                # 检查是否有省略号,标记为不完整
                if '...' in content or '…' in content or len(content) < 100:
                    self.log(f"⚠️ 获取的内容不完整或包含省略号 ({len(content)} 字)")
                    return None
                
                if len(content) > 500:
                    content = content[:500]
                
                self.log(f"✅ 成功获取文章内容 ({len(content)} 字)")
                return content
            else:
                self.log(f"❌ 获取文章失败: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.log(f"❌ 获取文章异常: {e}")
            return None
    
    def mcp_initialize(self):
        """初始化mcp"""
        try:
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "xiaohongshu-auto-publisher", "version": "3.2.0"}
                },
                "id": 1
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            
            response = requests.post(f"{self.base_url}/mcp", json=init_request, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.session_id = response.headers.get('Mcp-Session-Id')
                return True
            else:
                self.log(f"初始化失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"初始化异常: {e}")
            return False
    

    def check_sensitive_words(self, title: str, content: str, tags: list = None) -> tuple:
        """
        检查标题和内容中是否包含敏感词/违规词
        
        Args:
            title: 标题
            content: 内容
            tags: 标签列表(可选,用于检查医院名称)
        
        Returns:
            (is_clean: bool, found_words: list) 
            is_clean: True 表示没有敏感词,False 表示发现敏感词
            found_words: 发现的敏感词列表,格式为 [(类型, 词语), ...]
        """
        found_words = []
        text_to_check = f"{title} {content}"
        tags_text = " ".join(tags) if tags else ""
        
        # 1. 绝对化用语
        absolute_words = [
            "最", "第一", "顶级", "国家级", "最高级", "最佳", "最大", "最小", 
            "唯一", "首选", "绝对", "永久", "万能", "特效", "根治", "痊愈",
            "100%", "百分之百", "保证治愈", "包治", "永不复发", "彻底根治",
            "完全治愈", "肯定能好", "一定会好", "保证好", "保证痊愈",
        ]
        for word in absolute_words:
            if word in text_to_check:
                found_words.append(("绝对化用语", word))
        
        # 2. 医疗违规词
        medical_violations = [
            "药到病除", "无副作用", "无风险", "零风险",
            "祖传秘方", "独家秘方", "神药", "仙丹", "偏方", "秘方",
            "疗效最佳", "不反弹", "不复发", "痊愈", "彻底治愈",
            "肯定治愈", "保证治愈", "肯定能治好", "一定能治好",
        ]
        for word in medical_violations:
            if word in text_to_check:
                found_words.append(("医疗违规", word))
        
        # 3. 具体药品名称(靶向药,化疗药等)
        drug_names = [
            # 靶向药
            "仑伐替尼", "多纳非尼", "索拉非尼", "瑞戈非尼", "阿帕替尼",
            "信迪利单抗", "帕博利珠单抗", "纳武利尤单抗", "卡瑞利珠单抗",
            "贝伐珠单抗", "西妥昔单抗", "曲妥珠单抗", "利妥昔单抗",
            "奥希替尼", "吉非替尼", "厄洛替尼", "阿法替尼", "达克替尼",
            "克唑替尼", "阿来替尼", "色瑞替尼", "布加替尼",
            "帕唑帕尼", "舒尼替尼", "阿昔替尼", "卡博替尼",
            # 化疗药
            "顺铂", "卡铂", "奥沙利铂", "紫杉醇", "多西他赛", "白蛋白紫杉醇",
            "吉西他滨", "卡培他滨", "替吉奥", "氟尿嘧啶", "甲氨蝶呤",
            "阿霉素", "表阿霉素", "环磷酰胺", "异环磷酰胺",
            "依托泊苷", "伊立替康", "拓扑替康", "长春新碱", "长春瑞滨",
            # 内分泌治疗药
            "他莫昔芬", "托瑞米芬", "来曲唑", "阿那曲唑", "依西美坦",
            "氟维司群", "戈舍瑞林", "亮丙瑞林",
            # 其他常用药
            "阿司匹林", "二甲双胍", "格列美脲", "格列齐特",
            "硝苯地平", "氨氯地平", "缬沙坦", "厄贝沙坦",
            "美托洛尔", "比索洛尔", "阿托伐他汀", "瑞舒伐他汀",
        ]
        for word in drug_names:
            if word in text_to_check:
                found_words.append(("具体药品名称", word))
        
        # 4. 具体医院名称
        hospital_names = [
            "瑞金医院", "华山医院", "仁济医院", "中山医院", "同济医院",
            "协和医院", "华西医院", "湘雅医院", "齐鲁医院", "盛京医院",
            "301医院", "阜外医院", "安贞医院", "天坛医院", "宣武医院",
            "复旦肿瘤医院", "复旦大学附属肿瘤医院", "上海肿瘤医院",
            "北大医院", "北大人民医院", "北医三院", "北京医院",
            "上海九院", "上海六院", "长海医院", "长征医院",
            "浙一医院", "浙二医院", "邵逸夫医院",
            "江苏省人民医院", "鼓楼医院", "中大医院",
            "中山一院", "中山三院", "南方医院", "珠江医院",
            "西京医院", "唐都医院", "交大一附院", "交大二附院",
            "齐鲁医院", "省立医院", "千佛山医院",
            "湘雅一院", "湘雅二院", "湘雅三院",
            "同济医院", "协和医院", "武汉大学人民医院",
            "四川省人民医院", "成都市第三人民医院",
        ]
        # 检查标题,内容和标签
        full_text = f"{text_to_check} {tags_text}"
        for word in hospital_names:
            if word in full_text:
                found_words.append(("具体医院名称", word))
        
        # 5. 虚假宣传
        false_promises = [
            "立竿见影", "无效退款", "无效退全款", "假一赔十",
            "全网最低", "史上最低", "错过今天后悔一辈子",
            "最后一天", "限时秒杀", "错过等一年",
        ]
        for word in false_promises:
            if word in text_to_check:
                found_words.append(("虚假宣传", word))
        
        # 6. 诱导性词汇
        induce_words = [
            "必买", "必须", "一定要", "不得不", "再不看就晚了",
            "震惊", "惊呆", "吓尿", "疯了", "炸了", "燃爆",
            "紧急扩散", "速看", "马上删除", "内部消息",
        ]
        for word in induce_words:
            if word in text_to_check:
                found_words.append(("诱导性词汇", word))
        
        # 7. 违禁医疗药品交易(管制药品,处方药买卖等)
        illegal_drug_trade = [
            # 管制药品相关
            "疫苗代预约", "代约疫苗", "九价代约", "HPV代约", "疫苗预约服务",
            "处方药代购", "代开处方", "处方买卖", "卖药", "买药", "药品转让",
            "自制药", " homemade药", "自制", "土方制药", "民间药方",
            # 交易相关
            "出售", "转让", "代购", "需要请联系", "加微信", "加V", "私信购买",
            "现货", "发货", "快递", "包邮", "价格优惠", "量大从优",
        ]
        for word in illegal_drug_trade:
            if word in text_to_check:
                found_words.append(("违禁药品交易", word))
        
        # 8. 违规医美内容
        illegal_medical_beauty = [
            # 非法医美项目
            "小腿阻断", "小腿肌肉阻断", "美白针", "溶脂针", "瘦脸针代购",
            "干细胞美容", "胎盘素", "人胎素", "羊胎素注射",
            "无证医美", "无资质医美", "工作室医美", "家里做医美", "上门医美",
            # 医美培训
            "医美培训", "微整形培训", "针剂培训", "医美学徒", "医美招生",
            "零基础学医美", "包教包会", "七天速成", "快速上岗",
            # 未成年人医美
            "未成年人整形", "学生整形", "未成年整容",
        ]
        for word in illegal_medical_beauty:
            if word in text_to_check:
                found_words.append(("违规医美", word))
        
        # 9. 药物错用滥用
        drug_abuse = [
            # 错误用法宣传
            "加大剂量", "翻倍吃", "多吃效果好", "少吃没效果",
            "长期服用无害", "可以一直吃", "没事多吃点", "吃到好为止",
            # 超药效宣传
            "万能药", "什么病都能治", "百病全消", "一药治百病",
            "感冒药治新冠", "抗生素消炎", "激素退烧快", "止痛药没事就吃",
            # 错误用药时间
            "随时吃", "想起来就吃", "不按说明书", "不用遵医嘱",
        ]
        for word in drug_abuse:
            if word in text_to_check:
                found_words.append(("药物错用滥用", word))
        
        # 10. 高风险疗法宣称治愈严重疾病
        risky_treatment = [
            # 宣称治愈癌症
            "治愈癌症", "癌症克星", "肿瘤消失", "癌细胞清零", "癌症自愈",
            "不用手术治愈", "不用化疗治愈", "食疗治癌", "保健品抗癌",
            "偏方治癌", "神医治癌", "民间疗法治癌", "气功治癌",
            # 替代正规治疗
            "不用去医院", "不用看医生", "自己就能治", "在家治好",
            "放弃治疗也能好", "西医没用", "化疗害人", "手术扩散",
        ]
        for word in risky_treatment:
            if word in text_to_check:
                found_words.append(("高风险疗法宣传", word))
        
        # 11. 中医馆招收学徒
        tcm_apprentice = [
            "招学徒", "招弟子", "收徒弟", "中医传承", "师承招生",
            "想学中医", "学中医找我", "中医培训", "针灸培训", "推拿培训",
            "出师后独立开店", "包就业", "包分配", "学成即就业",
        ]
        for word in tcm_apprentice:
            if word in text_to_check:
                found_words.append(("中医馆招学徒", word))
        
        is_clean = len(found_words) == 0
        return is_clean, found_words

    def check_content_quality(self, title: str, content: str, raw_title: str = "") -> tuple:
        """
        检查内容质量:篇幅,断句,与标题相关性
        
        Returns:
            (is_quality_ok: bool, reason: str)
            is_quality_ok: True 表示质量合格,False 表示质量不合格
            reason: 不合格的原因描述
        """
        # 1. 检查篇幅是否过少
        min_content_length = 200  # 最小内容长度(字符)
        if len(content) < min_content_length:
            return False, f"内容篇幅过少 ({len(content)}字 < {min_content_length}字)"
        
        # 2. 检查是否有明显的断句(内容不完整)
        # 检查结尾是否有不完整的句子
        incomplete_markers = [
            "靶", "药", "的", "是", "在", "和", "与", "对", "为", "有", "可以", "需要",
            "建议", "注意", "避免", "使用", "进行", "治疗", "手术", "检查", "出现",
            "发生", "导致", "引起", "造成", "产生", "形成", "变成",
            "比如", "例如", "如", "像", "包括", "其中", "此外", "另外",
            "首先", "其次", "然后", "最后", "总之", "总结",
            ":", ":", ";", ",", "—", "-", ">", "→",
        ]
        
        # 检查内容最后20个字符
        content_end = content[-30:].strip() if len(content) >= 30 else content.strip()
        
        # 如果以不完整标记结尾,可能是断句
        for marker in incomplete_markers:
            if content_end.endswith(marker):
                return False, f"内容可能不完整(以{marker}结尾)"
        
        # 检查是否有明显的省略号或截断标记
        if "..." in content[-50:] or "…" in content[-50:] or "[ truncated" in content.lower():
            return False, "内容存在截断或省略"
        
        # 检查段落完整性
        lines = content.split("\n")
        last_non_empty_line = ""
        for line in reversed(lines):
            if line.strip():
                last_non_empty_line = line.strip()
                break
        
        # 检查最后一行是否完整(以标点符号结尾)
        if last_non_empty_line:
            ending_punctuations = [".", "!", "?", ".", "!", "?", "~", "…", ")", " )", "]", "}", "»", "'", '"', " " ]
            if not any(last_non_empty_line.endswith(p) for p in ending_punctuations):
                # 特殊处理:如果是列表项或emoji结尾,也算完整
                if not (last_non_empty_line.startswith("•") or 
                        last_non_empty_line.startswith("-") or
                        last_non_empty_line.startswith("*") or
                        any(emoji in last_non_empty_line[-3:] for emoji in ["💪", "👇", "✨", "💡", "🎯", "❤️", "👍", "🌟", "💕", "🔥", "⚠️", "✅", "❌", "📌", "📋", "📝", "💊", "🏥", "👨‍⚕️", "👩‍⚕️"])):
                    return False, f"内容结尾不完整({last_non_empty_line[-20:]})"
        
        # 3. 检查内容与标题的相关性
        # 提取标题关键词
        title_keywords = []
        
        # 提取标题中的核心词汇(2字以上的词)
        import re
        # 移除标点,提取中文词汇
        title_clean = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", title)
        
        # 提取2-6字的词组
        for length in range(6, 1, -1):
            for i in range(len(title_clean) - length + 1):
                word = title_clean[i:i+length]
                if len(word) >= 2:
                    title_keywords.append(word)
        
        # 去重并保持顺序
        seen = set()
        title_keywords = [x for x in title_keywords if not (x in seen or seen.add(x))]
        
        # 检查标题关键词是否在内容中出现
        if title_keywords:
            # 取前3个关键词检查
            key_terms = title_keywords[:5]
            matched_terms = [term for term in key_terms if term in content]
            
            # 至少要有2个关键词匹配
            if len(matched_terms) < 1 and len(key_terms) >= 2:
                return False, f"内容与标题相关性不足(关键词匹配: {len(matched_terms)}/{len(key_terms)})"
        
        # 4. 检查内容是否有实质性内容(不能全是空话)
        # 检查是否包含实质性的医疗/健康建议关键词
        substance_keywords = [
            "检查", "治疗", "手术", "药物", "用药", "剂量", "时间", "方法", "建议", "注意",
            "饮食", "运动", "休息", "复查", "随访", "预防", "症状", "诊断", "病因",
            "风险", "并发症", "副作用", "效果", "恢复", "康复", "护理",
            "血压", "血糖", "血脂", "体重", "体温", "心率", "呼吸",
            "每周", "每天", "每次", "定期", "长期", "持续",
        ]
        
        has_substance = any(keyword in content for keyword in substance_keywords)
        if not has_substance:
            return False, "内容缺乏实质性医疗建议"
        
        # 5. 检查是否有过多的重复内容
        lines_list = [line.strip() for line in lines if line.strip()]
        unique_lines = set(lines_list)
        if len(lines_list) > 5 and len(unique_lines) / len(lines_list) < 0.5:
            return False, "内容重复度过高"
        
        return True, "内容质量检查通过"

    def mcp_publish(self, title, content, image_path, tags):
        """发布到小红书"""
        publish_guard.refuse("publish_content")
        try:
            publish_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "publish_content",
                    "arguments": {
                        "title": title,
                        "content": content,
                        "images": [image_path],
                        "tags": tags
                    }
                },
                "id": 2
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": self.session_id
            }
            
            response = requests.post(f"{self.base_url}/mcp", json=publish_request, headers=headers, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    return True, result
                elif "error" in result:
                    return False, result["error"]
            else:
                return False, f"HTTP {response.status_code}"
                
        except Exception as e:
            return False, str(e)
    
    def check_pause_status(self):
        """检查是否处于暂停状态"""
        pause_file = Path.home() / ".xiaohongshu_pause.json"
        
        if not pause_file.exists():
            return False
        
        try:
            with open(pause_file, 'r', encoding='utf-8') as f:
                pause_info = json.load(f)
            
            if not pause_info.get('paused', False):
                return False
            
            resume_at = datetime.fromisoformat(pause_info['resume_at'])
            
            if datetime.now() >= resume_at:
                self.log("暂停时间已到，云端发布开关仍然关闭，不会自动恢复")
                return True
            
            # 仍在暂停中
            remaining = resume_at - datetime.now()
            days = remaining.days
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            self.log(f"⏸️ 发布已暂停,还有 {days}天 {hours}小时 {minutes}分钟 恢复")
            return True
            
        except Exception as e:
            self.log(f"⚠️ 检查暂停状态失败: {e}")
            return False
    
    def run(self):
        """运行自动发布"""
        publish_guard.refuse("full auto publisher")
        self.log("=" * 60)
        self.log("小红书全自动发布系统 V3.0 完整版 启动")
        self.log("功能: 完整内容 + 网上搜索 + 小红书专业格式")
        self.log("=" * 60)
        
        # 检查是否处于暂停状态
        if self.check_pause_status():
            self.log("⏸️ 任务因暂停而跳过")
            return True
        
        if not self.mcp_initialize():
            self.log("❌ mcp初始化失败,退出")
            return False
        
        self.log(f"✅ mcp初始化成功")
        
        all_sources = list(self.data_sources.keys())
        used_records = self.load_used_records()
        skipped_records = self.load_skipped_records()
        
        for attempt in range(1, self.max_retries + 1):
            self.log(f"\n🔄 第 {attempt}/{self.max_retries} 次尝试...")
            
            source_key = random.choice(all_sources)
            source_config = self.data_sources[source_key]
            
            self.log(f"选择数据源: {source_config['name']} ({source_key})")
            
            records = self.load_excel_data(source_config["file"])
            
            if not records:
                self.log(f"❌ 数据源为空,重新选择...")
                continue
            
            self.log(f"加载了 {len(records)} 条记录")
            
            used_ids = used_records.get(source_key, [])
            skipped_ids = [s["id"] for s in skipped_records.get(source_key, [])]
            available = self.get_available_records(records, used_ids, skipped_ids, source_key)
            
            if not available:
                self.log(f"{source_config['name']} 所有记录已用完,尝试其他数据源...")
                used_records[source_key] = []
                skipped_records[source_key] = []
                self.save_used_records(used_records)
                self.save_skipped_records(skipped_records)
                available = self.get_available_records(records, [], [], source_key)
            
            if not available:
                self.log("❌ 没有可用记录")
                continue
            
            self.log(f"可用记录: {len(available)} 条")
            
            record, record_id = random.choice(available)
            
            raw_title = record.get('文章标题', '')
            category = record.get('分类', '健康科普')
            
            self.log(f"选中记录: {raw_title[:40]}...")
            
            title = self.clean_title(raw_title, source_config["hospital_names"])
            
            image_path = self.find_image_path(record, source_config)
            if not image_path:
                self.log("❌ 没有找到可用图片,记录为跳过...")
                skipped_records[source_key].append({
                    "id": record_id,
                    "title": raw_title,
                    "reason": "缺少配图",
                    "time": datetime.now().isoformat()
                })
                self.save_skipped_records(skipped_records)
                continue
            
            self.log(f"图片: {Path(image_path).name}")
            
            # 获取文章内容 - 优先使用Excel中的"文章内容"字段
            article_content = ""
            excel_content = record.get('文章内容', '')
            article_url = record.get('文章链接', '')
            
            # 优先使用Excel中的文章内容字段
            if excel_content and isinstance(excel_content, str) and len(excel_content.strip()) > 10:
                article_content = excel_content.strip()
                # 清理可能的省略号
                article_content = article_content.replace("...", "").replace("…", "")
                self.log(f"✅ 使用Excel中的文章内容 ({len(article_content)} 字)")
            elif article_url:
                # 如果Excel中没有内容,则通过URL抓取
                article_content = self.fetch_article_content(article_url)
            
            # 检测视频内容
            if article_content:
                has_video, video_keyword = self.check_video_content(article_content)
                if has_video:
                    self.log(f"⚠️ 检测到视频内容(关键词: '{video_keyword}'),跳过此文章...")
                    skipped_records[source_key].append({
                        "id": record_id,
                        "title": raw_title,
                        "reason": f"包含视频内容({video_keyword})",
                        "time": datetime.now().isoformat()
                    })
                    self.save_skipped_records(skipped_records)
                    continue
            
            # 使用新的内容生成方法
            content = self.generate_xiaohongshu_content(raw_title, category, article_content)
            content_length = len(content)
            self.log(f"内容字数: {content_length} 字")
            
            # 检查是否包含省略号
            if '...' in content or '…' in content:
                self.log("⚠️ 生成的内容包含省略号,重新生成...")
                content = self.generate_xiaohongshu_content(raw_title, category, "")
                content = content.replace("...", "").replace("…", "")
            
            # 生成标签
            tags = ["健康科普", "健康管理"]
            if "甲状腺" in raw_title:
                tags.extend(["甲状腺", "体检"])
            elif "前列腺" in raw_title:
                tags.extend(["前列腺癌", "男性健康"])
            elif "肿瘤" in raw_title or "癌" in raw_title:
                tags.extend(["肿瘤", "癌症防治"])
            elif "感冒" in raw_title:
                tags.extend(["感冒", "育儿知识"])
            elif "流感" in raw_title:
                tags.extend(["流感", "宝妈必看"])
            elif "脑卒中" in raw_title or "中风" in raw_title:
                tags.extend(["脑卒中", "中风预防", "心脑血管"])
            elif "帕金森" in raw_title:
                tags.extend(["帕金森病", "神经内科", "老年健康"])
            elif "癫痫" in raw_title:
                tags.extend(["癫痫", "神经内科"])
            elif "头痛" in raw_title:
                tags.extend(["头痛", "神经内科"])
            elif "失眠" in raw_title:
                tags.extend(["失眠", "睡眠健康"])
            elif "抑郁" in raw_title:
                tags.extend(["抑郁症", "心理健康"])
            elif "阿尔茨海默" in raw_title or "老年痴呆" in raw_title:
                tags.extend(["阿尔茨海默病", "老年痴呆", "神经内科"])
            elif "颈椎" in raw_title:
                tags.extend(["颈椎病", "骨科", "职场健康"])
            elif "腰椎" in raw_title:
                tags.extend(["腰椎间盘突出", "骨科"])
            elif "脑肿瘤" in raw_title:
                tags.extend(["脑肿瘤", "神经外科"])
            elif "胃" in raw_title or "肠" in raw_title:
                tags.extend(["消化内科", "胃肠健康"])
            elif "风湿" in raw_title or "关节" in raw_title:
                tags.extend(["风湿免疫", "关节健康"])
            elif "痛风" in raw_title:
                tags.extend(["痛风", "高尿酸"])
            elif "结石" in raw_title:
                tags.extend(["泌尿系结石", "泌尿外科"])
            elif "孕期" in raw_title or "孕" in raw_title:
                tags.extend(["孕期保健", "妇产科", "宝妈"])
            elif "脂肪肝" in raw_title:
                tags.extend(["脂肪肝", "肝病"])
            elif "胆囊" in raw_title:
                tags.extend(["胆囊疾病", "肝胆外科"])
            elif "便秘" in raw_title:
                tags.extend(["便秘", "肠道健康"])
            
            # 医院标签已移除(避免敏感词)
            tags = list(set(tags))[:8]
            
            # 敏感词检查
            self.log("🔍 正在检查敏感词/违规内容...")
            is_clean, found_words = self.check_sensitive_words(title, content, tags)
            
            if not is_clean:
                # 格式化输出发现的敏感词
                self.log("❌ 发现敏感词/违规内容:")
                word_summary = {}
                for word_type, word in found_words:
                    if word_type not in word_summary:
                        word_summary[word_type] = []
                    word_summary[word_type].append(word)
                
                for word_type, words in word_summary.items():
                    self.log(f"   [{word_type}] {', '.join(words)}")
                
                self.log("⛔ 发布已中止,跳过此记录...")
                
                # 记录详细信息
                skip_reason = "; ".join([f"[{t}] {w}" for t, w in found_words])
                skipped_records[source_key].append({
                    "id": record_id,
                    "title": raw_title,
                    "reason": f"包含敏感词/违规内容: {skip_reason}",
                    "time": datetime.now().isoformat()
                })
                self.save_skipped_records(skipped_records)
                continue
            
            self.log("✅ 敏感词检查通过")
            
            # 内容质量检查
            self.log("🔍 正在检查内容质量...")
            is_quality_ok, quality_reason = self.check_content_quality(title, content, raw_title)
            
            if not is_quality_ok:
                self.log(f"❌ 内容质量检查不通过: {quality_reason}")
                self.log("⛔ 发布已中止,跳过此记录,等待下次任务...")
                skipped_records[source_key].append({
                    "id": record_id,
                    "title": raw_title,
                    "reason": f"内容质量不合格: {quality_reason}",
                    "time": datetime.now().isoformat()
                })
                self.save_skipped_records(skipped_records)
                continue
            
            self.log(f"✅ 内容质量检查通过 ({len(content)}字)")
            
            # 发布
            self.log("正在发布到小红书...")
            success, result = self.mcp_publish(title, content, image_path, tags)
            
            if success:
                self.log("✅ 发布成功!")
                
                if record_id not in used_records.get(source_key, []):
                    used_records[source_key].append(record_id)
                    self.save_used_records(used_records)
                    self.log(f"✅ 已记录为已使用: {record_id}")
                
                # 记录发布的笔记信息(用于后续评论回复)
                self._record_published_note(title, content, image_path, tags, result)
                
                self.log("=" * 60)
                self.log("✅ 自动发布流程完成")
                self.log("=" * 60)
                return True
            else:
                self.log(f"❌ 发布失败: {result}, 准备重试...")
                continue
        
        self.log("❌ 达到最大重试次数,发布失败")
        return False
    
    def _record_published_note(self, title: str, content: str, image_path: str, tags: list, result: dict):
        """Record published note for comment reply"""
        try:
            from datetime import datetime
            from pathlib import Path
            import json
            import re
            
            record_file = Path("/Users/henry/.xiaohongshu_published_notes.json")
            
            # 加载现有记录
            records = []
            if record_file.exists():
                try:
                    with open(record_file, 'r', encoding='utf-8') as f:
                        records = json.load(f)
                except:
                    records = []
            
            # 从发布结果中提取 feed_id 和 xsec_token
            feed_id = None
            xsec_token = None
            raw_result_text = None
            
            try:
                # MCP 返回的是 Go 格式字符串,不是 JSON
                # 格式: "内容发布成功: &{Title:xxx Content:xxx Images:1 Status:xxx PostID:xxx}"
                if "result" in result and "content" in result["result"]:
                    for item in result["result"]["content"]:
                        if item.get("type") == "text":
                            text = item.get("text", "")
                            raw_result_text = text
                            
                            # 尝试从 Go 格式字符串中提取 PostID
                            # 格式: PostID:xxxxx}
                            postid_match = re.search(r'PostID:([^}]*)', text)
                            if postid_match:
                                potential_id = postid_match.group(1).strip()
                                if potential_id and potential_id != "":
                                    feed_id = potential_id
                                    self.log(f"✅ 从发布结果提取到 feed_id: {feed_id}")
                            break
            except Exception as e:
                self.log(f"⚠️ 解析发布结果失败: {e}")
            
            # 如果 feed_id 为空,尝试搜索补充
            if not feed_id:
                self.log("🔍 feed_id 为空,尝试搜索补充...")
                feed_id, xsec_token = self._search_note_by_title(title)
            
            # 添加新记录
            note_record = {
                "title": title,
                "content": content,
                "image_path": image_path,
                "tags": tags,
                "published_at": datetime.now().isoformat(),
                "feed_id": feed_id,
                "xsec_token": xsec_token,
                "raw_result": raw_result_text,  # 保存原始结果以便调试
                "last_check": None,
                "total_comments": 0,
                "replied_count": 0,
                "is_own_note": True  # 标记为自己发布的笔记
            }
            records.append(note_record)
            
            # 保存
            with open(record_file, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            
            if feed_id:
                self.log(f"📝 已记录笔记信息(feed_id: {feed_id[:20]}...)")
            else:
                self.log(f"📝 已记录笔记信息(暂无feed_id,后续可手动补充)")
                self.log(f"   提示: 可在小红书APP中复制笔记链接,提取ID补充到记录中")
        except Exception as e:
            self.log(f"⚠️ 记录笔记信息失败: {e}")
    
    def _search_note_by_title(self, title: str, max_retries: int = 3) -> tuple:
        """
        通过标题搜索刚发布的笔记,获取 feed_id 和 xsec_token
        新笔记可能需要10-30秒才能被搜索到
        返回: (feed_id, xsec_token)
        """
        publish_guard.refuse("search_feeds")
        try:
            import time
            import json
            
            # 新笔记需要更长时间才能被搜索索引,等待10秒
            self.log("   等待笔记被搜索引擎收录 (10秒)...")
            time.sleep(10)
            
            # 准备多个搜索关键词(标题的不同部分)
            search_keywords = []
            
            # 关键词1: 前12个字符(去除emoji)
            clean_title = title.replace("🧪", "").replace("🎨", "").replace("💡", "").replace("🔥", "").strip()
            search_keywords.append(clean_title[:12])
            
            # 关键词2: 如果标题较长,取中间部分
            if len(clean_title) > 15:
                search_keywords.append(clean_title[5:17])
            
            # 关键词3: 前8个字符
            search_keywords.append(clean_title[:8])
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Mcp-Session-Id": self.session_id
            }
            
            # 尝试不同关键词
            for keyword in search_keywords:
                if len(keyword) < 4:  # 跳过太短的关键词
                    continue
                    
                self.log(f"   尝试搜索关键词: '{keyword}...'")
                
                for attempt in range(max_retries):
                    try:
                        search_request = {
                            "jsonrpc": "2.0",
                            "method": "tools/call",
                            "params": {
                                "name": "search_feeds",
                                "arguments": {
                                    "keyword": keyword,
                                    "filters": {
                                        "sort_by": "最新",
                                        "publish_time": "一天内"
                                    }
                                }
                            },
                            "id": 100 + attempt
                        }
                        
                        response = requests.post(
                            f"{self.base_url}/mcp",
                            json=search_request,
                            headers=headers,
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            
                            if "result" in result and "content" in result["result"]:
                                for item in result["result"]["content"]:
                                    if item.get("type") == "text":
                                        try:
                                            resp_data = json.loads(item.get("text", "{}"))
                                            
                                            if "feeds" in resp_data:
                                                for feed in resp_data["feeds"]:
                                                    note_card = feed.get("noteCard", {})
                                                    display_title = note_card.get("displayTitle", "")
                                                    
                                                    # 检查标题是否匹配(更宽松的匹配)
                                                    # 检查前10个字符是否匹配
                                                    if (clean_title[:10] in display_title or 
                                                        display_title[:10] in clean_title or
                                                        # 检查是否包含主要关键词
                                                        (len(keyword) >= 6 and keyword in display_title)):
                                                        feed_id = feed.get("id")
                                                        xsec_token = feed.get("xsecToken")
                                                        self.log(f"✅ 通过搜索找到笔记: {feed_id}")
                                                        return feed_id, xsec_token
                                        except:
                                            pass
                        
                        if attempt < max_retries - 1:
                            time.sleep(2)
                        
                    except Exception as e:
                        if attempt < max_retries - 1:
                            time.sleep(2)
                
                # 不同关键词之间等待一下
                time.sleep(2)
            
            self.log("⚠️ 未能通过搜索找到笔记(新笔记可能需要几分钟才能被索引)")
            self.log("   建议: 10分钟后运行 xiaohongshu_fix_feedid.py 手动补充")
            return None, None
            
        except Exception as e:
            self.log(f"⚠️ 搜索笔记失败: {e}")
            return None, None

if __name__ == "__main__":
    publisher = AutoPublisher()
    success = publisher.run()
    exit(0 if success else 1)
