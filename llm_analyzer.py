from langchain_community.document_loaders import TextLoader
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import datetime
import logging
from typing import List, Dict

class LLMAnalyzer:
    def __init__(self, api_key: str, model_name: str, base_url: str):
        self.llm = OpenAI(
            api_key=api_key,
            model_name=model_name,
            base_url=base_url,
            max_tokens=8192
        )
        self.logger = logging.getLogger(__name__)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=20000,
            chunk_overlap=1000,
            length_function=len
        )

    def _generate_tables(self, posts: List[Dict], time_ranges: Dict, translator) -> Dict:
        """生成分析表格"""
        def filter_posts(start_time):
            filtered = []
            for p in posts:
                try:
                    post_time = datetime.datetime.strptime(p['created'], "%Y-%m-%d %H:%M")
                    if post_time >= start_time:
                        filtered.append(p)
                except:
                    continue
            return filtered
        
        # 按时间范围分类
        daily = sorted(filter_posts(time_ranges["24h"]), 
                      key=lambda x: x.get('comment_count', 0), reverse=True)[:10]
        weekly = sorted(filter_posts(time_ranges["week"]), 
                       key=lambda x: x.get('comment_count', 0), reverse=True)[:7]
        monthly = sorted(filter_posts(time_ranges["month"]), 
                        key=lambda x: x.get('comment_count', 0), reverse=True)[:5]
        
        # 生成Markdown表格
        def make_table(data, title):
            if not data:
                return f"### {title}\n无数据\n"
            table = [
                f"### {title}",
                "| 原标题 | 中文标题 | 标签 | 评分 |",
                "|------|------|------|------|"
            ]
            for p in data:
                title = p.get('title', '无标题')
                flair = p.get('flair', '未知')
                created = p.get('created', '未知时间')
                comments = p.get('comment_count', 0)
                score = p.get('score', 0)
                url = p.get('url', '#')
                
                table.append(
                    f"| [{title}]({url}) | {translator.translate(title)} | {flair} | {score} |"
                )
            return "\n".join(table)
        
        return {
            "daily": make_table(daily, "24小时热门"),
            "weekly": make_table(weekly, "本周热门"), 
            "monthly": make_table(monthly, "本月热门")
        }

    def generate_report(self, raw_data_file: str, report_file: str, time_ranges: Dict, translator) -> bool:
        """生成分析报告"""
        try:
            # 加载原始数据
            if not os.path.exists(raw_data_file):
                raise FileNotFoundError("原始数据文件不存在")
                
            loader = TextLoader(raw_data_file, encoding="utf-8")
            documents = loader.load()
            
            # 处理长文本
            texts = self.text_splitter.split_text(documents[0].page_content)
            
            # 获取所有帖子数据用于生成表格
            all_posts = []
            with open(raw_data_file, "r", encoding="utf-8") as f:
                current_post = {}
                for line in f:
                    if line.startswith("【帖子ID】"):
                        if current_post:
                            all_posts.append(current_post)
                        current_post = {"id": line.strip().split()[-1]}
                    elif line.startswith("【标题】"):
                        current_post["title"] = line[4:].strip()
                    elif line.startswith("【标签】"):
                        current_post["flair"] = line[4:].strip()
                    elif line.startswith("【时间】"):
                        parts = line[4:].strip().split("|")
                        current_post["created"] = parts[0].strip()
                        if len(parts) > 1:
                            current_post["score"] = parts[1].replace("评分:", "").strip()
                    elif line.startswith("【评论数】"):
                        current_post["comment_count"] = int(line[5:].strip())
                    elif line.startswith("【原文链接】"):
                        current_post["url"] = line[6:].strip()
            
            # 生成表格
            tables = self._generate_tables(all_posts, time_ranges, translator)
            # 生成报告内容
            prompt = PromptTemplate(
                input_variables=["content", "date", "tables"],
                template="""
作为Reddit分析师，请根据以下数据生成报告：

当前日期: {date}

今日主要讨论的帖子: {tables}

原始数据样本: {content}

请用中文撰写今日主要趋势分析，严格按照以下格式输出，不要添加其他标题或内容：

## 今日主要趋势分析
(在这里分析当前的主要讨论趋势和热点话题)
"""
            )
            
            chain = LLMChain(llm=self.llm, prompt=prompt)
            self.logger.info("开始生成报告...")
            report_content = chain.run(
                content=texts[0][:15000],  # 使用第一个文本块
                date=datetime.datetime.utcnow().strftime("%Y年%m月%d日"),
                tables="\n\n".join(tables.values())
            )
            # 保存报告
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(tables.get("daily", ""))
                f.write("\n\n")
                f.write(report_content.replace("Assistant: ",""))
                f.write("\n\n> 本内容由AI自动生成，读者自行辨别\n")
            
            self.logger.info(f"报告生成成功: {report_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"生成报告失败: {str(e)[:200]}")
            return False
