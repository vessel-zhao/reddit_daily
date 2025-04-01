import praw
import datetime
import time
import logging
from typing import List, Dict

class RedditClient:
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        self.logger = logging.getLogger(__name__)
        
    def load_subreddits(self, file_path: str = "subreddits.txt") -> List[str]:
        """加载subreddit列表"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            self.logger.error(f"Subreddit列表文件 {file_path} 未找到")
            return []

    def fetch_posts(self, subreddit_name: str, time_ranges: Dict, max_posts: int = 10) -> List[Dict]:
        """获取指定subreddit的帖子"""
        posts = []
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            self.logger.info(f"开始获取 r/{subreddit_name} 的内容...")
            
            post_count = 0
            for submission in subreddit.hot(limit=100):
                try:
                    post_time = datetime.datetime.fromtimestamp(submission.created_utc)
                    if post_time < time_ranges["month"]:
                        continue
                        
                    if post_count >= max_posts:
                        break
                        
                    # 处理评论
                    submission.comments.replace_more(limit=1)
                    comments = []
                    for comment in submission.comments.list()[:20]:  # 最多20条评论
                        if isinstance(comment, praw.models.Comment):  # 确保是评论对象
                            comments.append(f"{getattr(comment.author, 'name', '[已删除]')}: {comment.body[:300]}")

                    # 构建帖子数据字典
                    post = {
                        "id": submission.id,
                        "title": submission.title,
                        "content": submission.selftext if submission.selftext else "",
                        "author": str(getattr(submission.author, 'name', '[已删除]')),
                        "created": post_time.strftime("%Y-%m-%d %H:%M"),
                        "score": submission.score,
                        "comments": comments,
                        "comment_count": len(comments),
                        "url": f"https://reddit.com{submission.permalink}",
                        "subreddit": subreddit_name,
                        "flair": submission.link_flair_text  # 新增flair字段
                    }
                    posts.append(post)
                    post_count += 1
                    time.sleep(0.5)
                    
                except Exception as e:
                    self.logger.warning(f"处理帖子 {submission.id} 时出错: {str(e)[:100]}")
                    time.sleep(1)
            
            self.logger.info(f"从 r/{subreddit_name} 获取了 {len(posts)} 条帖子")
            return posts
            
        except Exception as e:
            self.logger.error(f"获取subreddit {subreddit_name} 时出错: {str(e)[:200]}")
            return []