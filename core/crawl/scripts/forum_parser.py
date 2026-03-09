from core.crawl.scripts.base_parser import BaseParser
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

class ForumParser(BaseParser):
    """
    论坛页面解析器
    支持解析常见的论坛帖子格式，包括问题帖和回答帖
    """
    
    def supports(self, url: str, content: str) -> bool:
        """
        判断是否支持解析传入的网页内容格式
        从URL和内容两个维度检查是否包含论坛相关特征
        """
        # 从URL维度检查
        parsed_url = urlparse(url.lower())
        url_path = parsed_url.path
        
        # URL中包含论坛相关关键词
        url_forum_keywords = ['forum', 'forums', 'thread', 'topic', 'post', 'discussion', 'q&a', 'qa']
        for keyword in url_forum_keywords:
            if keyword in url_path:
                return True
        
        # 从内容维度检查
        content_lower = content.lower()
        
        forum_keywords = ['forum', '论坛', 'post', 'thread', 'topic', 'discussion', '帖子', '回复', 'question', 'answer']
        for keyword in forum_keywords:
            if keyword in content_lower:
                return True
        
        # 检查是否包含常见的论坛HTML结构
        if ('class="post"' in content or 'class="thread"' in content or 
            'class="reply"' in content or '<div class="question">' in content or
            'class="forum"' in content or 'id="forum"' in content):
            return True
            
        return False
    
    def parse(self, url: str, content: str) -> list:
        """
        解析网页内容，返回其中包含的问题和答案
        返回格式为 [{'question': '...', 'answer': '...'}, ...]
        """
        try:
            soup = BeautifulSoup(content, 'html.parser')
            qa_pairs = []
            
            # 基于URL信息进行特殊处理
            parsed_url = urlparse(url)
            url_path_parts = [part for part in parsed_url.path.split('/') if part]
            
            # 如果URL路径包含thread或topic，可能是单个帖子页面
            if any(part in ['thread', 'topic', 'post'] for part in url_path_parts):
                # 查找标题作为问题
                title_selectors = ['h1', 'h2', '.title', '.subject', '.post-title']
                for selector in title_selectors:
                    title_element = soup.select_one(selector)
                    if title_element:
                        title_text = title_element.get_text(strip=True)
                        if title_text and (title_text.endswith('?') or title_text.endswith('？')):
                            # 查找第一个帖子内容作为答案
                            content_selectors = ['.post-content', '.message', '.content', '.post-body']
                            for content_selector in content_selectors:
                                content_element = soup.select_one(content_selector)
                                if content_element:
                                    content_text = content_element.get_text(strip=True)
                                    if content_text and len(content_text) > 20:
                                        qa_pairs.append({
                                            'question': title_text,
                                            'answer': content_text[:500]  # 限制答案长度
                                        })
                                        break
                            break
            
            # 如果还没有找到，使用通用解析逻辑
            if not qa_pairs:
                # 查找问题和回答
                # 模式1: 问题在特定的容器中
                question_containers = soup.find_all(class_=re.compile(r'(?:question|title|subject)', re.I))
                for container in question_containers:
                    question = container.get_text(strip=True)
                    if question and (question.endswith('?') or question.endswith('？')):
                        # 查找对应的答案
                        answer_containers = soup.find_all(class_=re.compile(r'(?:answer|reply|response|content)', re.I))
                        for answer_container in answer_containers:
                            answer = answer_container.get_text(strip=True)
                            if answer and len(answer) > 20:  # 确保答案有一定长度
                                qa_pairs.append({
                                    'question': question,
                                    'answer': answer
                                })
                                break  # 每个问题只匹配一个答案
            
            # 如果没有找到问题，尝试从整个页面提取
            if not qa_pairs:
                # 查找以问号结尾的句子作为问题
                text = soup.get_text()
                sentences = re.split(r'[。！？!?]+', text)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence and (sentence.endswith('?') or sentence.endswith('？')):
                        qa_pairs.append({
                            'question': sentence,
                            'answer': text[:500]  # 使用页面主要内容作为答案
                        })
            
            return qa_pairs
            
        except Exception as e:
            print(f"ForumParser解析错误: {e}")
            return []