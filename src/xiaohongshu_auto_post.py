#!/usr/bin/env python3
"""
小红书自动发布脚本
每天定时从瑞金医院或肿瘤医院Excel中随机选择记录发布
"""

import os
import json
import random
from datetime import datetime
from pathlib import Path

def load_excel_data(excel_path):
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
            records.append(record)
        return records
    except Exception as e:
        print(f"加载Excel失败: {e}")
        return []

def load_used_records():
    """加载已使用的记录"""
    used_file = Path("/Users/henry/.xiaohongshu_used_records.json")
    if used_file.exists():
        with open(used_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"ruijin": [], "zhongliu": []}

def save_used_records(used_records):
    """保存已使用的记录"""
    used_file = Path("/Users/henry/.xiaohongshu_used_records.json")
    with open(used_file, 'w', encoding='utf-8') as f:
        json.dump(used_records, f, ensure_ascii=False, indent=2)

def get_available_records(records, used_ids, source):
    """获取可用记录"""
    available = []
    for record in records:
        record_id = f"{source}_{record.get('序号', '')}"
        if record_id not in used_ids:
            available.append((record, record_id))
    return available

def generate_content(title, category):
    """根据标题和分类生成小红书内容"""
    content = f"💡 {title}\n\n"
    
    if "甲状腺" in title:
        content += "甲状腺健康不容忽视！\n"
        content += "定期体检，早发现早治疗是关键。\n\n"
        content += "📌 注意事项：\n"
        content += "• 保持良好作息\n"
        content += "• 合理摄入碘盐\n"
        content += "• 定期复查B超\n"
        content += "• 遵医嘱治疗\n"
    elif "前列腺" in title:
        content += "关注男性健康，科学认识疾病。\n\n"
        content += "📌 关键信息：\n"
        content += "• 定期体检筛查\n"
        content += "• 关注身体变化\n"
        content += "• 新技术带来新希望\n"
        content += "• 积极治疗，乐观面对\n"
    elif "感冒" in title or "流感" in title:
        content += "季节交替，注意防护！\n\n"
        content += "📌 预防措施：\n"
        content += "• 勤洗手，戴口罩\n"
        content += "• 多通风，少聚集\n"
        content += "• 均衡饮食，适量运动\n"
        content += "• 及时接种疫苗\n"
    elif "雾化" in title:
        content += "儿童雾化治疗注意事项。\n\n"
        content += "📌 操作要点：\n"
        content += "• 药量遵医嘱\n"
        content += "• 清洁消毒很重要\n"
        content += "• 保持正确姿势\n"
        content += "• 观察孩子反应\n"
    else:
        content += "健康知识科普，帮助大家更好地管理健康。\n\n"
        content += "📌 健康建议：\n"
        content += "• 定期体检\n"
        content += "• 健康饮食\n"
        content += "• 适量运动\n"
        content += "• 如有不适及时就医\n"
    
    content += "\n🎯 温馨提示：\n"
    content += "健康管理需要长期坚持，希望大家都能拥有健康的身体！\n\n"
    content += "内容仅供参考，如有不适请及时就医。"
    
    return content

def get_tags(category, title):
    """根据分类和标题获取标签"""
    base_tags = ["健康科普", "健康管理"]
    
    if "甲状腺" in title:
        base_tags.extend(["甲状腺", "体检", "B超"])
    elif "前列腺" in title:
        base_tags.extend(["前列腺癌", "男性健康", "抗癌"])
    elif "感冒" in title or "流感" in title:
        base_tags.extend(["感冒", "流感", "儿童健康"])
    elif "雾化" in title:
        base_tags.extend(["雾化", "儿童护理", "育儿知识"])
    elif category == "疾病科普":
        base_tags.extend(["疾病预防", "医学知识"])
    elif category == "儿童健康":
        base_tags.extend(["儿童健康", "育儿知识"])
    
    return list(set(base_tags))[:8]  # 最多8个标签

def main():
    """主函数 - 仅输出要发布的信息"""
    print(f"[{datetime.now()}] 开始执行自动发布任务...")
    
    # Excel文件路径
    ruijin_excel = "/Users/henry/Downloads/瑞金医院公众号保健文章汇总.xlsx"
    zhongliu_excel = "/Users/henry/Downloads/上海肿瘤医院公众号保健文章汇总.xlsx"
    
    # 随机选择来源
    source = random.choice(["ruijin", "zhongliu"])
    print(f"选择来源: {source}")
    
    # 加载数据
    if source == "ruijin":
        records = load_excel_data(ruijin_excel)
        image_prefix = "xiaohongshu_"
    else:
        records = load_excel_data(zhongliu_excel)
        image_prefix = "zhongliu_"
    
    if not records:
        print("没有可发布的记录")
        return None
    
    # 加载已使用记录
    used_records = load_used_records()
    used_ids = used_records.get(source, [])
    
    # 获取可用记录
    available = get_available_records(records, used_ids, source)
    
    if not available:
        print(f"{source} 所有记录已发布完毕，重置记录...")
        used_records[source] = []
        save_used_records(used_records)
        available = get_available_records(records, [], source)
    
    if not available:
        print("没有可用记录")
        return None
    
    # 随机选择一条
    record, record_id = random.choice(available)
    
    # 获取信息
    title = record.get('文章标题', '')
    category = record.get('分类', '健康科普')
    image_path = record.get('配图路径', '')
    
    # 构建完整图片路径
    if image_path:
        full_image_path = f"/Users/henry/Downloads/{image_path}"
    else:
        # 根据序号选择默认图片
        seq = record.get('序号', 1)
        if source == "ruijin":
            full_image_path = f"/Users/henry/Downloads/xiaohongshu_{seq}_babeichong.png"
        else:
            full_image_path = f"/Users/henry/Downloads/zhongliu_{seq}_jiazhuangxian.png"
    
    # 检查图片是否存在
    if not Path(full_image_path).exists():
        # 尝试其他图片
        import glob
        if source == "ruijin":
            images = glob.glob(f"/Users/henry/Downloads/xiaohongshu_*.png")
        else:
            images = glob.glob(f"/Users/henry/Downloads/zhongliu_*.png")
        
        if images:
            full_image_path = random.choice(images)
        else:
            print("没有找到可用图片")
            return None
    
    print(f"选中记录: {title}")
    print(f"分类: {category}")
    print(f"图片: {full_image_path}")
    print(f"记录ID: {record_id}")
    
    # 生成内容
    content = generate_content(title, category)
    tags = get_tags(category, title)
    
    # 输出发布信息供外部脚本使用
    result = {
        "title": title[:20] + "..." if len(title) > 20 else title,
        "content": content,
        "image": full_image_path,
        "tags": tags,
        "record_id": record_id,
        "source": source
    }
    
    # 保存发布信息
    info_file = Path("/Users/henry/.xiaohongshu_post_info.json")
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 发布信息已保存")
    return result

if __name__ == "__main__":
    main()
