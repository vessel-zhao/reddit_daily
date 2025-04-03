import datetime
import time
import logging
import os
from reddit_client import RedditClient
from translation_utils import TranslationUtils
from llm_analyzer import LLMAnalyzer
from dotenv import load_dotenv
from json_converter import convert_to_js
from md_to_image import convert_md_to_image

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    filename="reddit_analyzer_fixed.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="w",
    encoding="utf-8"
)
logger = logging.getLogger()

 # 初始化各组件
reddit_client = RedditClient(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

translator = TranslationUtils(
    access_key_id=os.getenv("TRANSLATION_ACCESS_KEY_ID"),
    access_key_secret=os.getenv("TRANSLATION_ACCESS_KEY_SECRET")
)

llm_analyzer = LLMAnalyzer(
    api_key=os.getenv("LLM_API_KEY"),
    model_name=os.getenv("LLM_MODEL_NAME"),
    base_url=os.getenv("LLM_BASE_URL")
)

def ensure_date_directory(date_str: str) -> str:
    """确保日期目录存在，返回目录路径"""
    dir_path = os.path.join("reports", date_str)
    os.makedirs(dir_path, exist_ok=True)
    return dir_path

def main():
    try:
        # 初始化时间变量
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        date_dir = ensure_date_directory(current_date)
        
        raw_data_file = os.path.join(date_dir, f"reddit_raw_{current_date}.txt")
        report_file = os.path.join(date_dir, f"reddit_report_{current_date}.md")
        
        # 时间范围
        now = datetime.datetime.utcnow()
        time_ranges = {
            "24h": now - datetime.timedelta(hours=24),
            "week": now - datetime.timedelta(days=7),
            "month": now - datetime.timedelta(days=30)
        }

        # 执行分析流程
        logger.info("启动Reddit分析流程")
        
        subreddits = reddit_client.load_subreddits()
        if not subreddits:
            logger.error("未找到有效的subreddit列表")
            return False
            
        logger.info(f"将分析以下subreddit: {', '.join(subreddits)}")
        
        # 检查原始数据文件是否已存在且有效
        if os.path.exists(raw_data_file) and os.path.getsize(raw_data_file) > 100:
            logger.info(f"检测到已有数据文件 {raw_data_file}，直接生成报告")
            return llm_analyzer.generate_report(raw_data_file, report_file, time_ranges, translator)
        
        # 如果文件不存在或无效，则初始化并采集数据
        with open(raw_data_file, "w", encoding="utf-8") as f:
            f.write(f"Reddit数据采集\n")
            f.write(f"采集时间: {now.strftime('%Y-%m-%d %H:%M UTC')}\n")
            f.write(f"目标subreddit: {', '.join(subreddits)}\n")
            f.write("="*60 + "\n\n")
        
        # 收集数据
        all_posts = []
        for subreddit in subreddits:
            posts = reddit_client.fetch_posts(subreddit, time_ranges)
            all_posts.extend(posts)
            time.sleep(2)
        
        # 保存原始数据
        with open(raw_data_file, "a", encoding="utf-8") as f:
            for post in all_posts:
                f.write(f"\n【帖子ID】 {post['id']}\n")
                f.write(f"【标题】 {post['title']}\n")
                f.write(f"【作者】 {post['author']}\n")
                f.write(f"【时间】 {post['created']} | 评分: {post['score']}\n")
                f.write(f"【评论数】 {post['comment_count']}\n")
                f.write(f"【内容】\n{post['content'][:2000]}\n")
                f.write(f"【标签】{post['flair']}")
                f.write("\n【热门评论】\n")
                for i, comment in enumerate(post['comments'], 1):
                    f.write(f"{i}. {comment}\n")
                f.write(f"\n【原文链接】 {post['url']}\n")
                f.write("-"*50 + "\n")
        
        # 生成报告
        if os.path.exists(raw_data_file) and os.path.getsize(raw_data_file) > 100:
            success = llm_analyzer.generate_report(raw_data_file, report_file, time_ranges, translator)
            if success:
                logger.info(f"文件已保存到: {date_dir}")
            return success
        else:
            logger.error("没有收集到有效数据")
            return False
    except Exception as e:
        logger.error(f"主程序发生异常: {str(e)}", exc_info=True)
        return False

def preview_report(report_path):
    """预览报告"""
    try:
        # 获取所在的日期目录和文件名
        dir_path = os.path.dirname(report_path)
        base_name = os.path.basename(report_path)
        
        # 设置预览图片路径（与 md 文件位于同一目录）
        preview_filename = os.path.splitext(base_name)[0] + '.png'
        preview_path = os.path.join(dir_path, preview_filename)
        
        # 生成预览图片
        convert_md_to_image(report_path, preview_path, width=600)
        
        # 检查预览图片是否生成成功
        if os.path.exists(preview_path) and os.path.getsize(preview_path) > 0:
            print(f"预览图片已生成: {preview_path}")
            return True
        else:
            print("预览图片生成失败")
            return False
            
    except Exception as e:
        print(f"预览生成错误: {str(e)}")
        return False
    
def move_to_lastest():
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    print(f"\n分析完成！\n- 数据目录: reports/{current_date}\n"
            f"- 原始数据: reddit_raw_{current_date}.txt\n"
            f"- 分析报告: reddit_report_{current_date}.md")
    
    # 新增：创建last文件夹并写入最新文件
    last_dir = os.path.join("reports", "lastest")
    os.makedirs(last_dir, exist_ok=True)
    
    # 定义最新文件路径
    last_raw_txt = os.path.join(last_dir, "lastest_raw.txt")
    last_raw_js = os.path.join(last_dir, "lastest_raw.js")
    last_report_md = os.path.join(last_dir, "lastest_report.md")
    last_report_png = os.path.join(last_dir, "lastest_report.png")
    
    # 获取当前日期文件路径
    raw_data_file = os.path.join("reports", current_date, f"reddit_raw_{current_date}.txt")
    report_file = os.path.join("reports", current_date, f"reddit_report_{current_date}.md")
    
    # 复制文件到last文件夹
    try:
        # 复制原始数据文件
        with open(raw_data_file, 'r', encoding='utf-8') as src, \
                open(last_raw_txt, 'w+', encoding='utf-8') as dst:
            dst.write(src.read())
        logger.info(f"转换js文件: {last_raw_js}")
        # 转换并保存JS文件
        convert_to_js(raw_data_file, last_raw_js,translator)
        
        # 复制报告文件
        with open(report_file, 'r', encoding='utf-8') as src, \
                open(last_report_md, 'w+', encoding='utf-8') as dst:
            dst.write(src.read())
        
        print(f"- 最新文件已保存到: {last_dir}")
        print(f"生成图片中...")
        # 转换并保存图片
        convert_md_to_image(
            last_report_md,
            last_report_png,
            width=600
        )
    except Exception as e:
        print(f"\n最新文件保存失败: {str(e)}")
    else:
        print("\n分析过程中出现错误，请查看日志文件")

if __name__ == "__main__":
    print("Reddit分析工具启动...")
    
    if main():
        move_to_lastest()