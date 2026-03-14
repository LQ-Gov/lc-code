import re, requests
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
from datetime import datetime
import cloudscraper
from core.crawl.scripts.base_parser import BaseParser

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
                    # 检查是否为类且继承自BaseParser（但不是BaseParser本身）
                    if isinstance(attr, type) and issubclass(attr, BaseParser) and attr != BaseParser:
                        try:
                            parser_instance = attr()
                            parser_instances.append(parser_instance)
                        except Exception as e:
                            print(f"Error creating instance of {attr_name} from {filename}: {e}")
                            continue
                        
            except Exception as e:
                print(f"Error loading parser script {filename}: {e}")
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

    scraper = cloudscraper.create_scraper(browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    })

    response = scraper.get(url)
    
    
    return response

def is_qa_page_with_llm(content: str) -> bool:
    """Use LLM to determine if a page is a QA page"""
    try:
        model = get_qwen_model()
        
        prompt = ChatPromptTemplate.from_template(
            """Analyze the following webpage content and determine if it contains ACTUAL question-answer pairs 
            with both questions AND their corresponding answers in the same page.
            
            IMPORTANT DISTINCTIONS:
            - A TRUE QA page contains specific questions WITH their detailed answers on the same page
            - A LIST/INDEX/TOC page only contains links or titles pointing to other pages, WITHOUT actual answers
            - Directory pages, section listings, and navigation pages are NOT QA pages
            - Only pages with concrete Q&A content should be considered QA pages
            
            Examples of NON-QA pages (should return 'NO'):
            - Pages with only headings like "Card application", "Delivery", "FAQ" without answers
            - Pages that list topics with links to other pages
            - Table of contents or navigation pages
            - Category listing pages
            
            Examples of TRUE QA pages (should return 'YES'):
            - Pages with actual questions like "How do I apply for a card?" followed by detailed answers
            - Pages containing both the question text AND the answer text in the same document
            - FAQ pages where each question is immediately followed by its answer
            
            Webpage Content:
            {content}
            
            Respond with ONLY 'YES' if it's a TRUE QA page with actual questions AND answers, or 'NO' if it's not."""
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
        
        # Extract only the body content from HTML
        body_content = content
        body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.IGNORECASE | re.DOTALL)
        if body_match:
            body_content = body_match.group(1)
        
        # Common patterns that likely indicate QA/FAQ/help pages
        qa_patterns = [
            r'faq', r'question', r'answer', r'help', r'support', 
            r'knowledge', r'guide', r'tutorial', r'how-?to', r'article'
        ]
        
        # Find all URLs in the body content (both absolute and relative)
        # Match href and src attributes in HTML
        url_matches = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', body_content, re.IGNORECASE)
        
        # Also match URLs that might be in other contexts within body
        url_matches.extend(re.findall(r'https?://[^\s"\'<>]+', body_content))
        
        valid_urls = []
        base_domain = urlparse(base_url).netloc
        
        for url in url_matches:
            # Skip empty URLs
            if not url.strip():
                continue
                
            # Skip anchor links (starting with #)
            if url.startswith('#'):
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
                
            # Skip CSS and JS files (check path as well)
            if parsed_url.path.lower().endswith(('.css', '.js')):
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
                
        return unique_urls  # Limit to 10 URLs
            
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
            
            IMPORTANT: This page has been confirmed to contain ACTUAL question-answer pairs with both questions AND answers.
            Do NOT generate parsers for list/index pages that only contain links or titles without actual answers.
            
            The class should be named appropriately based on the content type (e.g., FAQParser, HelpCenterParser, etc.).
            It must implement two methods with EXACT signatures:
            1. supports(self, url: str, content: str) -> bool: returns True if the parser can handle this URL and content combination.
               Use both URL patterns (path, domain, query parameters) and content structure to make the decision.
               The supports method should ONLY return True for pages that contain ACTUAL Q&A content, NOT list/index pages.
            2. parse(self, url: str, content: str) -> list: returns a list of dictionaries with 'question' and 'answer' keys.
               Each dictionary must have exactly these two keys: 'question' and 'answer'.
               The format should be [{{'question': '...', 'answer': '...'}}, ...].
               Only extract pairs where BOTH question and answer are present and non-empty.
            
            Webpage URL: {url}
            Sample Content:
            {content}
            
            IMPORTANT REQUIREMENTS:
            - Generate ONLY the complete Python class code, nothing else before or after.
            - MUST include the import statement: "from core.crawl.scripts.base_parser import BaseParser"
            - Include proper docstring and comprehensive error handling in both methods.
            - Ensure the code is syntactically correct and will execute without errors.
            - Handle edge cases like missing questions/answers, malformed HTML, etc.
            - Make sure the class is robust and can handle variations in the page structure.
            - The parse method MUST return a list of dictionaries, NOT a dict with 'questions' and 'answers' keys.
            - Always validate that extracted questions and answers are non-empty strings.
            - The supports method should be strict and only match pages with actual Q&A content.
            - Avoid matching directory pages, section listings, or navigation pages.
            
            Example of CORRECT output format:
            ```python
            from core.crawl.scripts.base_parser import BaseParser
            import re
            from bs4 import BeautifulSoup
            
            class FAQParser(BaseParser):
                \"\"\"Parser for FAQ pages with actual Q&A content\"\"\"
                
                def supports(self, url: str, content: str) -> bool:
                    # Implementation here - should be strict about actual Q&A content
                    pass
                    
                def parse(self, url: str, content: str) -> list:
                    # Implementation here - extract only actual Q&A pairs
                    pass
            ```
            
            The class should be saved in the core/crawl/scripts/ directory."""
        )
        
        chain = prompt | model | StrOutputParser()
        parser_script = chain.invoke({
            "url": url,
            "content": content[:1500]  # Limit content length
        })
        
        # Clean up the response if it contains extra text or markdown code blocks
        parser_script = parser_script.strip()
        if parser_script.startswith('```python'):
            parser_script = parser_script[9:]  # Remove ```python
        if parser_script.endswith('```'):
            parser_script = parser_script[:-3]  # Remove ```
        parser_script = parser_script.strip()
        
        # Validate syntax before returning
        try:
            compile(parser_script, '<generated>', 'exec')
            return parser_script
        except SyntaxError as e:
            print(f"Generated parser script has syntax error: {e}")
            # Try to fix common issues
            fixed_script = parser_script
            # Remove any remaining markdown indicators
            fixed_script = fixed_script.replace('```', '')
            # Ensure proper indentation
            lines = fixed_script.split('\n')
            fixed_lines = []
            indent_level = 0
            for line in lines:
                stripped = line.strip()
                if stripped:
                    if stripped.endswith(':'):
                        fixed_lines.append('    ' * indent_level + stripped)
                        indent_level += 1
                    elif stripped in ['pass', 'continue', 'break']:
                        fixed_lines.append('    ' * indent_level + stripped)
                    elif any(stripped.startswith(keyword) for keyword in ['elif', 'else', 'except', 'finally']):
                        if indent_level > 0:
                            fixed_lines.append('    ' * (indent_level - 1) + stripped)
                        else:
                            fixed_lines.append(stripped)
                    else:
                        fixed_lines.append('    ' * indent_level + stripped)
                else:
                    fixed_lines.append(line)
            fixed_script = '\n'.join(fixed_lines)
            
            # Try compiling again
            try:
                compile(fixed_script, '<generated>', 'exec')
                return fixed_script
            except SyntaxError:
                print("Failed to fix syntax errors in generated parser script")
                return ""
        
    except Exception as e:
        print(f"Error generating parser script: {e}")
        return ""

def generate_skip_parser_script_with_llm(content: str, url: str) -> str:
    """Generate a parser script using LLM for non-QA pages that should be skipped"""
    try:
        model = get_qwen_model()
        
        prompt = ChatPromptTemplate.from_template(
            """You are an expert web scraper developer. Analyze the following webpage content and URL 
            and generate a Python class that inherits from BaseParser and can identify similar non-QA pages to skip them.
            
            This page has been determined to NOT contain actual question-answer pairs with both questions AND answers.
            Common types of non-QA pages include:
            - List/index pages that only contain links or titles pointing to other pages
            - Directory pages, section listings, and navigation pages  
            - Category listing pages (like help center sections)
            - Pages with only headings without detailed answers
            - Table of contents or overview pages
            
            The class should be named appropriately based on the content type (e.g., SkipListPageParser, SkipDirectoryParser, etc.).
            It must implement two methods with EXACT signatures:
            1. supports(self, url: str, content: str) -> bool: returns True if the parser can handle this URL and content combination.
               Use both URL patterns (path, domain, query parameters) and content structure to make the decision.
               This should match pages that are NOT QA pages (like list pages, directory pages, index pages, etc.).
               Be specific about the patterns that indicate this is a non-QA page type.
            2. parse(self, url: str, content: str) -> list: returns an empty list [] since this is a non-QA page.
               Since this is a non-QA page, we don't want to extract any content from it.
            
            Webpage URL: {url}
            Sample Content:
            {content}
            
            IMPORTANT REQUIREMENTS:
            - Generate ONLY the complete Python class code, nothing else before or after.
            - MUST include the import statement: "from core.crawl.scripts.base_parser import BaseParser"
            - Include proper docstring and comprehensive error handling in both methods.
            - Ensure the code is syntactically correct and will execute without errors.
            - Handle edge cases like malformed HTML, etc.
            - The parse method MUST return an empty list [] (not None) to indicate no QA content.
            - Make sure the class is robust and can handle variations in the page structure.
            - The supports method should be specific to the type of non-QA page (e.g., list pages, directory pages).
            - Focus on identifying structural patterns that indicate this is NOT a true Q&A page.
            
            Example of CORRECT output format:
            ```python
            from core.crawl.scripts.base_parser import BaseParser
            import re
            from bs4 import BeautifulSoup
            
            class SkipHelpCenterSectionParser(BaseParser):
                \"\"\"Parser for skipping help center section/list pages that only contain links\"\"\"
                
                def supports(self, url: str, content: str) -> bool:
                    # Implementation here - should return True for similar non-QA pages
                    # Check for patterns like section listings, directory structures, etc.
                    pass
                    
                def parse(self, url: str, content: str) -> list:
                    # Return empty list to indicate no QA content
                    return []
            ```
            
            The class should be saved in the core/crawl/scripts/ directory."""
        )
        
        chain = prompt | model | StrOutputParser()
        parser_script = chain.invoke({
            "url": url,
            "content": content[:1500]  # Limit content length
        })
        
        # Clean up the response if it contains extra text or markdown code blocks
        parser_script = parser_script.strip()
        if parser_script.startswith('```python'):
            parser_script = parser_script[9:]  # Remove ```python
        if parser_script.endswith('```'):
            parser_script = parser_script[:-3]  # Remove ```
        parser_script = parser_script.strip()
        
        # Validate syntax before returning
        try:
            compile(parser_script, '<generated>', 'exec')
            return parser_script
        except SyntaxError as e:
            print(f"Generated skip parser script has syntax error: {e}")
            # Try to fix common issues
            fixed_script = parser_script
            # Remove any remaining markdown indicators
            fixed_script = fixed_script.replace('```', '')
            # Ensure proper indentation
            lines = fixed_script.split('\n')
            fixed_lines = []
            indent_level = 0
            for line in lines:
                stripped = line.strip()
                if stripped:
                    if stripped.endswith(':'):
                        fixed_lines.append('    ' * indent_level + stripped)
                        indent_level += 1
                    elif stripped in ['pass', 'continue', 'break']:
                        fixed_lines.append('    ' * indent_level + stripped)
                    elif any(stripped.startswith(keyword) for keyword in ['elif', 'else', 'except', 'finally']):
                        if indent_level > 0:
                            fixed_lines.append('    ' * (indent_level - 1) + stripped)
                        else:
                            fixed_lines.append(stripped)
                    else:
                        fixed_lines.append('    ' * indent_level + stripped)
                else:
                    fixed_lines.append(line)
            fixed_script = '\n'.join(fixed_lines)
            
            # Try compiling again
            try:
                compile(fixed_script, '<generated>', 'exec')
                return fixed_script
            except SyntaxError:
                print("Failed to fix syntax errors in generated skip parser script")
                return ""
        
    except Exception as e:
        print(f"Error generating skip parser script: {e}")
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
        # if is_qa_page_with_llm(content):
        #     discovered_urls.append(url)

        # Extract potential QA links from the page using LLM
        qa_links = extract_question_answer_links(content, url)
        discovered_urls.extend(qa_links)
    
    # Remove duplicates and limit to reasonable number
    discovered_urls = list(set(discovered_urls))
    
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
            
        response = fetch_webpage_content(url)

        content = response.text
        
        parsed_data = []
        parser_found = False
        
        # 尝试所有动态加载的解析脚本
        for parser in available_parsers:
            try:
                print(f"Trying dynamic parser: {parser.__class__.__name__} for {url}")
                if parser.supports(url, content):  # 传入url和content两个参数
                    print(f"Using dynamic parser {parser.__class__.__name__} for {url}")
                    parsed_data = parser.parse(url, content)  # 传入url和content两个参数
                    if parsed_data is not None:  # 即使是空列表也认为找到了解析器
                        parser_found = True
                        break
            except Exception as e:
                print(f"Dynamic parser {parser.__class__.__name__} failed: {e}")
                continue
        
        # 如果所有现有解析脚本都不支持，则生成新的解析脚本
        if not parser_found:
            print(f"No existing parser supports {url}, generating new parser")
            if not is_qa_page_with_llm(content):
                # 网页不是QA页面，生成一个跳过该类型页面的解析脚本
                skip_parser_script = generate_skip_parser_script_with_llm(content, url)
                if skip_parser_script:
                    # 保存跳过解析脚本到scripts目录
                    try:
                        # 提取类名来生成文件名
                        class_match = re.search(r'class\s+(\w+)\s*\(', skip_parser_script)
                        if class_match:
                            class_name = class_match.group(1)
                            # 生成时间戳（格式：yyyyMMddHHmmss）
                            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                            script_filename = f"{class_name.lower()}_{timestamp}.py"
                            script_path = os.path.join("core", "crawl", "scripts", script_filename)
                            
                            # 确保目录存在
                            os.makedirs(os.path.dirname(script_path), exist_ok=True)
                            
                            # 保存脚本文件
                            with open(script_path, 'w', encoding='utf-8') as f:
                                f.write(skip_parser_script)
                           
                            
                            print(f"Saved skip parser script to {script_path}")
                        
                    except Exception as e:
                        print(f"Error saving skip parser script: {e}")
                # 跳过处理，不存储任何数据
                continue
            
            parser_script = generate_parser_script_with_llm(content, url)
            if parser_script:
                # 保存新生成的解析脚本到scripts目录
                try:
                    # 提取类名来生成文件名
                    class_match = re.search(r'class\s+(\w+)\s*\(', parser_script)
                    if class_match:
                        class_name = class_match.group(1)
                        # 生成时间戳（格式：yyyyMMddHHmmss）
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        script_filename = f"{class_name.lower()}_{timestamp}.py"
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
                                print(f"Trying dynamic parser: {parser.__class__.__name__} for {url}")
                                if parser.supports(url, content):  # 传入url和content两个参数
                                    print(f"Using dynamic parser {parser.__class__.__name__} for {url}")
                                    parsed_data = parser.parse(url, content)  # 传入url和content两个参数
                                    if parsed_data is not None:
                                        parser_found = True
                                        break
                            except Exception as e:
                                print(f"New parser {parser.__class__.__name__} failed: {e}")
                                continue
                
                except Exception as e:
                    print(f"Error saving parser script: {e}")
            
            # 如果生成的解析器仍然不工作，回退到直接LLM提取
            if not parser_found or parsed_data is None:
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
        
        # 如果parsed_data为None（比如skip parser的情况），跳过存储
        if parsed_data is None:
            continue
            
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