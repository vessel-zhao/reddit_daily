import json
import os
from typing import List, Dict
from translation_utils import TranslationUtils  # 新增导入翻译工具
import logging


# 配置日志
logging.basicConfig(
    filename="reddit_analyzer_fixed.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="w",
    encoding="utf-8"
)
logger = logging.getLogger()

def parse_raw_file(file_path: str, translator: TranslationUtils = None) -> List[Dict]:  # 新增translator参数
    """解析原始数据文件并返回结构化数据"""
    try:
        posts = []
        current_post = {}
        comments = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()  # 一次性读取所有行，便于处理内容块
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith("【帖子ID】"):
                    if current_post:
                        # 过滤分数低于50的帖子
                        if int(current_post.get("score", 0)) >= 50:
                            # 调用翻译功能
                            if translator:
                                # 翻译标题和内容
                                if 'title' in current_post:
                                    current_post['title'] = translator.translate(current_post['title'])
                                if 'content' in current_post:
                                    current_post['content'] = translator.translate(current_post['content'])
                            current_post["comments"] = comments
                            posts.append(current_post)
                    comments = []
                    current_post = {"id": line[7:].strip()}
                elif line.startswith("【标题】"):
                    current_post["title"] = line[4:].strip()
                elif line.startswith("【时间】"):
                    parts = line[4:].strip().split("|")
                    current_post["created"] = parts[0].strip()
                    if len(parts) > 1:
                        current_post["score"] = parts[1].replace("评分:", "").strip()
                elif line.startswith("【评论数】"):
                    current_post["comment_count"] = int(line[5:].strip())
                elif line.startswith("【内容】"):
                    current_post["content"] = ""
                    i += 1  # 移动到下一行
                    # 只提取【内容】和下一个【之间的内容
                    while i < len(lines) and not lines[i].strip().startswith("【"):
                        current_post["content"] += lines[i].strip() + "\n"
                        i += 1
                    i -= 1  # 回退一行，因为外层循环会再次增加i
                elif line.startswith("【标签】"):
                    current_post["flair"] = line[4:].strip()
                elif line.startswith("【热门评论】"):
                    i += 1  # 跳过【热门评论】行
                    continue
                elif line.startswith("【原文链接】"):
                    current_post["url"] = line[6:].strip()
                elif line.startswith("1.") or line.startswith("2.") or line.startswith("3."):
                    comment_text = line[3:].strip()
                    # 翻译评论内容
                    if translator:
                        comment_text = translator.translate(comment_text)
                    comments.append(comment_text)
                i += 1
    
        # 处理最后一个帖子
        if current_post and int(current_post.get("score", 0)) >= 50:
            current_post["comments"] = comments
            posts.append(current_post)
    
        # 根据score进行降序排序
        posts.sort(key=lambda x: int(x.get("score", 0)), reverse=True)
    
        return posts
    except Exception as e:
        logger.error(f"解析原始文件时发生异常: {str(e)}", exc_info=True)
        return []

def convert_to_js(input_file: str, output_file: str, translator: TranslationUtils = None):
    """将原始数据文件转换为JS格式"""
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"文件 {input_file} 不存在")
    
    posts = parse_raw_file(input_file, translator)
    
    js_content = f"window.postsData = {json.dumps(posts, ensure_ascii=False, indent=2)};"
    
    with open(output_file, 'w+', encoding='utf-8') as f:
        f.write(js_content)