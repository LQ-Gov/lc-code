from core.crawl.scripts.base_parser import BaseParser
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

class FAQParser(BaseParser):
    """
    FAQ页面解析器
    支持解析常见的FAQ页面格式，包括使用h3/h4标签作为问题，p/div标签作为答案的结构
    """
    
    def supports(self, url: str, content: str) -> bool:
        """
        判断是否支持解析传入的网页内容格式
        从URL和内容两个维度检查是否包含常见的FAQ特征
        """
        # 从URL维度检查
        parsed_url = urlparse(url.lower())
        url_path = parsed_url.path
        url_query = parsed_url.query
        
        # URL中包含FAQ相关关键词
        url_faq_keywords = ['faq', 'frequently-asked-questions', '常见问题', 'questions', 'help', 'support']
        for keyword in url_faq_keywords:
            if keyword in url_path or keyword in url_query:
                return True
        
        # 从内容维度检查
        content_lower = content.lower()
        
        # 检查是否包含FAQ相关关键词
        content_faq_keywords = ['faq', '常见问题', 'questions', 'answers', '问与答', '问答', 'frequently asked']
        for keyword in content_faq_keywords:
            if keyword in content_lower:
                return True
        
        # 检查是否包含常见的FAQ HTML结构
        if ('<h3' in content and '<p>' in content) or ('<h4' in content and '<div' in content):
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
            
            # 查找常见的FAQ结构
            # 模式1: h3/h4作为问题，紧随其后的p/div作为答案
            for header_tag in ['h3', 'h4']:
                headers = soup.find_all(header_tag)
                for header in headers:
                    question = header.get_text(strip=True)
                    if question:
                        # 查找紧随其后的段落或div作为答案
                        next_sibling = header.find_next_sibling()
                        if next_sibling and next_sibling.name in ['p', 'div']:
                            answer = next_sibling.get_text(strip=True)
                            if answer and len(answer) > 10:  # 确保答案有一定长度
                                qa_pairs.append({
                                    'question': question,
                                    'answer': answer
                                })
            
            # 模式2: 使用特定的class名称
            qa_elements = soup.find_all(class_=re.compile(r'(?:faq|question|answer)', re.I))
            if not qa_pairs and qa_elements:
                current_question = None
                for element in qa_elements:
                    text = element.get_text(strip=True)
                    if not text:
                        continue
                    
                    # 简单启发式：如果文本以问号结尾，认为是问题
                    if text.endswith('?') or text.endswith('？'):
                        current_question = text
                    elif current_question:
                        qa_pairs.append({
                            'question': current_question,
                            'answer': text
                        })
                        current_question = None
            
            # 如果仍然没有找到问题，可以基于URL信息进行特殊处理
            if not qa_pairs:
                parsed_url = urlparse(url.lower())
                url_path = parsed_url.path
                
                # 如果URL明确指向FAQ页面，但HTML结构不标准，尝试更宽松的解析
                if any(keyword in url_path for keyword in ['faq', '常见问题', 'help']):
                    # 提取所有以问号结尾的句子作为问题
                    all_text = soup.get_text()
                    sentences = re.split(r'[。！？!?]+', all_text)
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if sentence and (sentence.endswith('?') or sentence.endswith('？')):
                            qa_pairs.append({
                                'question': sentence,
                                'answer': all_text[:500]  # 限制答案长度
                            })
            
            return qa_pairs
            
        except Exception as e:
            print(f"FAQParser解析错误: {e}")
            return []