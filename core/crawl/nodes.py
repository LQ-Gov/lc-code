import re,requests
import os
import importlib.util
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
from core.crawl.state import CrawlState
from core.common.db import db_execute
from core.common.qwen_utils import get_qwen_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import hashlib
import json

def load_parser_scripts_from_directory(scripts_dir: str = "core/crawl/scripts") -> List[Any]:
    """
    动态加载scripts目录中的所有解析脚本类实例
    
    Args:
        scripts_dir (str): 脚本目录路径
        
    Returns:
        List[Any]: 解析器实例列表
    """
    parser_instances = []
    
    # 获取绝对路径
    if not os.path.isabs(scripts_dir):
        scripts_dir = os.path.join(os.getcwd(), scripts_dir)
    
    if not os.path.exists(scripts_dir):
        return parser_instances
    
    # 遍历目录中的所有Python文件
    for filename in os.listdir(scripts_dir):
        if filename.endswith('.py') and filename != '__init__.py' and filename != 'base_parser.py':
            file_path = os.path.join(scripts_dir, filename)
            try:
                # 动态导入模块
                spec = importlib.util.spec_from_file_location(filename[:-3], file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 查找继承自BaseParser的类
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        hasattr(attr, '__bases__') and 
                        any('BaseParser' in str(base) for base in attr.__bases__)):
                        # 创建实例并添加到列表
                        parser_instance = attr()
                        parser_instances.append(parser_instance)
                        
            except Exception as e:
                print(f"加载解析脚本 {filename} 时出错: {e}")
                continue
    
    return parser_instances

def fetch_webpage_content(url: str) -> str:
    """Mock function to fetch webpage content - replace with real HTTP requests in production"""
    # In real implementation, this would make HTTP requests using requests or httpx
    # return f"Mock HTML content for {url} containing various questions and answers about different topics."
    from urllib.parse import urlparse
    
    # 动态构建Referer，使用当前URL的域名
    parsed_url = urlparse(url)
    referer = f"{parsed_url.scheme}://{parsed_url.netloc}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': referer,
        'Connection': 'keep-alive',
        'Content-Type': 'text/html; charset=utf-8'
    }

    headers = {
        'User-Agent': 'PostmanRuntime/7.35.0',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': referer,
        'Connection': 'keep-alive',
        'Content-Type': 'text/html; charset=utf-8'
    }
    
    return requests.get(url, headers=headers)

def is_qa_page_with_llm(content: str) -> bool:
    """Use LLM to determine if a page is a QA page"""
    try:
        model = get_qwen_model()
        
        prompt = ChatPromptTemplate.from_template(
            """Analyze the following webpage content and determine if it contains question-answer pairs 
            or is structured as a Q&A format (like FAQ, forum posts, help pages, etc.).
            
            Webpage Content:
            {content}
            
            Respond with ONLY 'YES' if it's a QA page, or 'NO' if it's not."""
        )
        
        chain = prompt | model | StrOutputParser()
        result = chain.invoke({"content": content[:2000]})  # Limit content length
        
        return result.strip().upper() == 'YES'
    except Exception as e:
        print(f"Error in QA page detection: {e}")
        return False

def extract_question_answer_links(content: str, base_url: str) -> List[str]:
    """Extract potential QA page links from content using regex instead of LLM"""
    try:
        from urllib.parse import urljoin, urlparse
        
        # Common patterns that likely indicate QA/FAQ/help pages
        qa_patterns = [
            r'faq', r'question', r'answer', r'help', r'support', 
            r'knowledge', r'guide', r'tutorial', r'how-?to'
        ]
        
        # Find all URLs in the content (both absolute and relative)
        # Match href and src attributes in HTML
        url_matches = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', content, re.IGNORECASE)
        
        # Also match URLs that might be in other contexts
        url_matches.extend(re.findall(r'https?://[^\s"\'<>]+', content))
        
        valid_urls = []
        base_domain = urlparse(base_url).netloc
        
        for url in url_matches:
            # Skip empty URLs
            if not url.strip():
                continue
                
            # Skip CSS and JS files
            if url.lower().endswith(('.css', '.js')):
                continue
                
            # Convert relative URLs to absolute URLs
            absolute_url = urljoin(base_url, url)
            
            # Parse the absolute URL
            parsed_url = urlparse(absolute_url)
            
            # Skip non-http URLs
            if parsed_url.scheme not in ('http', 'https'):
                continue
                
            # Check if the URL path or query contains QA-related patterns
            url_path_and_query = (parsed_url.path + '?' + parsed_url.query).lower()
            if any(pattern in url_path_and_query for pattern in qa_patterns):
                valid_urls.append(absolute_url)
            # Also include URLs from the same domain as a fallback
            elif parsed_url.netloc == base_domain:
                # Exclude common non-content paths
                excluded_paths = ['/css/', '/js/', '/images/', '/img/', '/static/', '/assets/']
                if not any(excluded_path in parsed_url.path.lower() for excluded_path in excluded_paths):
                    valid_urls.append(absolute_url)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in valid_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
                
        return unique_urls[:10]  # Limit to 10 URLs
            
    except Exception as e:
        print(f"Error in link extraction: {e}")
        return []

def extract_qa_content_with_llm(content: str, url: str) -> dict:
    """Use LLM to extract question-answer pairs from content"""
    try:
        model = get_qwen_model()
        
        prompt = ChatPromptTemplate.from_template(
            """Analyze the following webpage content and extract question-answer pairs.
            
            Webpage URL: {url}
            Webpage Content:
            {content}
            
            Return a JSON object with 'questions' and 'answers' keys, each containing an array of strings.
            Example: {{"questions": ["What is your return policy?", "How long is the warranty?"], 
                      "answers": ["We offer a 30-day return policy", "The warranty is 1 year"]}}"""
        )
        
        chain = prompt | model | StrOutputParser()
        result_str = chain.invoke({
            "url": url,
            "content": content[:2000]  # Limit content length
        })
        
        # Try to parse the result as JSON
        try:
            # Clean up the response if it contains extra text
            start_idx = result_str.find('{')
            end_idx = result_str.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                result_str = result_str[start_idx:end_idx]
            
            result = json.loads(result_str)
            return {
                'questions': result.get('questions', []),
                'answers': result.get('answers', [])
            }
        except json.JSONDecodeError:
            # Fallback: extract Q&As using regex if LLM response is not valid JSON
            questions = re.findall(r'Q: (.+?)\n', result_str)
            answers = re.findall(r'A: (.+?)\n', result_str)
            
            return {
                'questions': questions,
                'answers': answers
            }
            
    except Exception as e:
        print(f"Error in QA content extraction: {e}")
        return {'questions': [], 'answers': []}

def generate_parser_script_with_llm(content: str, url: str) -> str:
    """Generate a parser script using LLM for the given content type"""
    try:
        model = get_qwen_model()
        
        prompt = ChatPromptTemplate.from_template(
            """You are an expert web scraper developer. Analyze the following webpage content and URL 
            and generate a Python class that inherits from BaseParser and can parse question-answer pairs from similar pages.
            
            The class should be named appropriately based on the content type (e.g., FAQParser, ForumParser, etc.).
            It must implement two methods:
            1. supports(self, url: str, content: str) -> bool: returns True if the parser can handle this URL and content combination.
               Use both URL patterns (path, domain, query parameters) and content structure to make the decision.
            2. parse(self, url: str, content: str) -> list: returns a list of dictionaries with 'question' and 'answer' keys.
               You can use both the URL and content to implement more intelligent parsing logic.
               The format should be [{'question': '...', 'answer': '...'}, ...].
            
            Webpage URL: {url}
            Sample Content:
            {content}
            
            Generate ONLY the complete Python class code, nothing else. Include proper docstring and error handling.
            Make sure the class is robust and can handle variations in the page structure.
            The class should be saved in the core/crawl/scripts/ directory."""
        )
        
        chain = prompt | model | StrOutputParser()
        parser_script = chain.invoke({
            "url": url,
            "content": content[:1500]  # Limit content length
        })
        
        return parser_script
    except Exception as e:
        print(f"Error generating parser script: {e}")
        return ""

def execute_parser_script(parser_script: str, url: str, content: str) -> list:
    """Execute a generated parser script"""
    try:
        # Create a namespace to execute the script
        namespace = {}
        exec(parser_script, namespace)
        
        # Find the parser class (should be the only class defined)
        parser_class = None
        for name, obj in namespace.items():
            if isinstance(obj, type):
                parser_class = obj
                break
        
        if parser_class:
            parser_instance = parser_class()
            return parser_instance.parse(url, content)  # 传入url和content两个参数
        else:
            return []
    except Exception as e:
        print(f"Error executing parser script: {e}")
        return []

def url_to_domain_key(url: str) -> str:
    """Convert URL to a domain key for caching"""
    parsed = urlparse(url)
    return f"{parsed.netloc}{parsed.path.split('/')[1] if len(parsed.path.split('/')) > 1 else ''}"

def discover_qa_urls_node(state: CrawlState) -> CrawlState:
    """Node 1: Analyze seed URL and find all suspected QA page URLs using LLM"""
    print(f"Round {state.round_count + 1}: Discovering QA URLs from seed: {state.seed_url}")
    
    # If this is the first round, start with the seed URL
    urls_to_process = [state.seed_url] if state.round_count == 0 else state.current_urls
    
    discovered_urls = []
    
    for url in urls_to_process:
        if url in state.processed_urls:
            continue
            
        response = fetch_webpage_content(url)

        content = response.text
        
        # Check if current page is already a QA page using LLM
        if is_qa_page_with_llm(content):
            discovered_urls.append(url)
        else:
            # Extract potential QA links from the page using LLM
            qa_links = extract_question_answer_links(content, url)
            discovered_urls.extend(qa_links)
    
    # Remove duplicates and limit to reasonable number
    discovered_urls = list(set(discovered_urls))[:20]
    
    # Update state
    new_state = CrawlState(
        seed_url=state.seed_url,
        current_urls=discovered_urls,
        round_count=state.round_count + 1,
        max_rounds=state.max_rounds,
        processed_urls=list(set(state.processed_urls + urls_to_process))
    )
    
    return new_state


def parse_and_store_node(state: CrawlState) -> CrawlState:
    """Node 2: Parse page content using LLM or cached scripts, store results in DB"""
    print(f"Round {state.round_count}: Parsing {len(state.current_urls)} URLs")
    
    # 动态加载所有解析脚本（每次调用都重新加载，确保包含新生成的脚本）
    available_parsers = load_parser_scripts_from_directory("core/crawl/scripts")
    
    for url in state.current_urls:
        if url in state.processed_urls:
            continue
            
        content = fetch_webpage_content(url)
        
        parsed_data = []
        parser_found = False
        
        # 尝试所有动态加载的解析脚本
        for parser in available_parsers:
            try:
                if parser.supports(url, content):  # 传入url和content两个参数
                    print(f"Using dynamic parser {parser.__class__.__name__} for {url}")
                    parsed_data = parser.parse(url, content)  # 传入url和content两个参数
                    if parsed_data:
                        parser_found = True
                        break
            except Exception as e:
                print(f"Dynamic parser {parser.__class__.__name__} failed: {e}")
                continue
        
        # 如果所有现有解析脚本都不支持，则生成新的解析脚本
        if not parser_found:
            print(f"No existing parser supports {url}, generating new parser")
            if not is_qa_page_with_llm(content):
                continue
            
            parser_script = generate_parser_script_with_llm(content, url)
            if parser_script:
                # 保存新生成的解析脚本到scripts目录
                try:
                    # 提取类名来生成文件名
                    class_match = re.search(r'class\s+(\w+)\s*\(', parser_script)
                    if class_match:
                        class_name = class_match.group(1)
                        script_filename = f"{class_name.lower()}.py"
                        script_path = os.path.join("core", "crawl", "scripts", script_filename)
                        
                        # 确保目录存在
                        os.makedirs(os.path.dirname(script_path), exist_ok=True)
                        
                        # 保存脚本文件
                        with open(script_path, 'w', encoding='utf-8') as f:
                            f.write(parser_script)
                        
                        print(f"Saved new parser script to {script_path}")
                        
                        # 重新加载解析器以包含新脚本
                        available_parsers = load_parser_scripts_from_directory("core/crawl/scripts")
                        
                        # 尝试使用新保存的解析器
                        for parser in available_parsers:
                            try:
                                if parser.supports(url, content):  # 传入url和content两个参数
                                    parsed_data = parser.parse(url, content)  # 传入url和content两个参数
                                    if parsed_data:
                                        parser_found = True
                                        break
                            except Exception as e:
                                print(f"New parser {parser.__class__.__name__} failed: {e}")
                                continue
                
                except Exception as e:
                    print(f"Error saving parser script: {e}")
            
            # 如果生成的解析器仍然不工作，回退到直接LLM提取
            if not parser_found or not parsed_data:
                print(f"Generated parser failed for {url}, falling back to direct LLM extraction")
                # 从LLM提取的内容转换为新的格式
                llm_result = extract_qa_content_with_llm(content, url)
                parsed_data = []
                questions = llm_result.get('questions', [])
                answers = llm_result.get('answers', [])
                
                # 确保一一对应
                min_len = min(len(questions), len(answers))
                for i in range(min_len):
                    parsed_data.append({
                        'question': questions[i],
                        'answer': answers[i]
                    })
        
        # 从parsed_data中提取唯一的问题，以question为key进行去重
        seen_questions = set()
        unique_qa_pairs = []
        for item in parsed_data:
            question = item.get('question', '')
            if question and question not in seen_questions:
                seen_questions.add(question)
                unique_qa_pairs.append(item)
        
        # 逐行存储到数据库
        for qa_pair in unique_qa_pairs:
            question = qa_pair.get('question', '').replace("|", " ")
            answer = qa_pair.get('answer', '').replace("|", " ")
            
            # 检查是否已存在相同URL和问题的记录
            existing_record = db_execute(
                """SELECT id FROM crawler_results 
                   WHERE current_url = ? AND questions = ?""", 
                (url, question)
            )
            
            if not existing_record:
                # 插入新记录
                db_execute(
                    """INSERT INTO crawler_results 
                       (seed_url, current_url, raw_content, questions, answers) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (state.seed_url, url, content[:5000], question, answer)  # Limit raw content size
                )
            else:
                # 更新现有记录
                db_execute(
                    """UPDATE crawler_results 
                       SET answers = ?, raw_content = ?
                       WHERE current_url = ? AND questions = ?""",
                    (answer, content[:5000], url, question)
                )
    
    # Update state (不再包含parsed_results的存储)
    new_state = CrawlState(
        seed_url=state.seed_url,
        current_urls=state.current_urls,
        round_count=state.round_count,
        max_rounds=state.max_rounds,
        processed_urls=state.processed_urls
    )
    
    return new_state

def should_continue_crawling(state: CrawlState) -> str:
    """Determine if crawling should continue based on round count and URLs found"""
    if state.round_count >= state.max_rounds:
        return "end"
    if not state.current_urls:
        return "end"
    return "discover"