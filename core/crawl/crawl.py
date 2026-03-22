import os
import sys
# 添加项目根目录到Python路径，以便能够导入core模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import hashlib
import asyncio
from typing import Dict, List, Set, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LXMLWebScrapingStrategy
from crawl4ai.chunking_strategy import IdentityChunking
from core.crawl.feature_extractor import PageFeatureExtractor, extract_qa_using_features
from core.crawl.llm_utils import is_qa_page_with_llm, extract_qa_content_with_llm
import time
import re
from datetime import datetime

class CrawlCallback:
    """
    爬虫回调基类，定义了爬虫完成、错误和关闭时的回调方法
    """
    
    async def finished(self, data: List[Dict], stats: Dict[str, Any] = None):
        """
        爬取完成时调用
        
        Args:
            data: 提取的Q&A数据列表
            stats: 爬取统计信息（可选）
        """
        pass
    
    async def error(self, error: Exception, url: str = None):
        """
        爬取发生错误时调用
        
        Args:
            error: 发生的异常
            url: 发生错误的URL（可选）
        """
        pass
    
    async def closed(self):
        """
        爬虫关闭时调用
        """
        pass


class QACrawler:
    """
    基于crawl4ai框架的Q&A数据提取爬虫
    使用特征缓存机制，特征基于URL和内容同时提取
    当无特征缓存时直接使用大模型提取Q&A内容，并反向生成特征
    对已爬取的网页直接跳过，避免重复处理
    """
    
    def __init__(self, max_depth: int = 2, output_file: Optional[str] = None, concurrency: int = 10, callback: CrawlCallback = None):
        self.max_depth = max_depth
        self.output_file = output_file
        self.concurrency = concurrency  # 并发数配置
        self.visited_urls: Set[str] = set()
        self.extracted_data: List[Dict] = []
        
        # 特征缓存：模板哈希 -> 特征字典（基于页面结构模板）
        self.feature_cache: Dict[str, Dict] = {}
        self.load_feature_cache()
        
        # 已爬取页面缓存：URL -> 处理状态
        self.crawled_pages: Dict[str, bool] = {}
        
        # 停止标志
        self.stopped = False
        
        # 回调对象
        self.callback = callback or CrawlCallback()
        
        # 配置crawl4ai用于纯HTML内容提取
        self.crawler_config = CrawlerRunConfig(
            process_in_browser=False,
            scraping_strategy=LXMLWebScrapingStrategy(),
            word_count_threshold=10,
            css_selector="body",
            chunking_strategy=IdentityChunking(),
            bypass_cache=False,
            only_text=False,
            parser_type="lxml",
            js_only=False,
            wait_until="load",
            page_timeout=30000,
        )
        
        # 创建可复用的AsyncWebCrawler实例
        self.crawler: Optional[AsyncWebCrawler] = None
        
    async def get_crawler(self) -> AsyncWebCrawler:
        """获取或创建AsyncWebCrawler实例"""
        if self.crawler is None:
            self.crawler = AsyncWebCrawler(
                verbose=False
            )
            await self.crawler.__aenter__()
        return self.crawler
    
    async def close(self):
        """清理资源并停止爬取"""
        self.stopped = True
        self.save_feature_cache()
        if self.crawler is not None:
            await self.crawler.__aexit__(None, None, None)
            self.crawler = None
        
        # 调用关闭回调
        try:
            await self.callback.closed()
        except Exception as e:
            print(f"Error in closed callback: {e}")
    
    def stop(self):
        """设置停止标志以停止爬取"""
        self.stopped = True
    
    def load_feature_cache(self):
        """从文件加载特征缓存"""
        cache_file = os.path.join(os.path.dirname(__file__), 'feature_cache.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.feature_cache = json.load(f)
                print(f"Loaded {len(self.feature_cache)} cached features")
            except Exception as e:
                print(f"Error loading feature cache: {e}")
    
    def save_feature_cache(self):
        """保存特征缓存到文件"""
        cache_file = os.path.join(os.path.dirname(__file__), 'feature_cache.json')
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.feature_cache, f, ensure_ascii=False, indent=2)
            print(f"Saved {len(self.feature_cache)} features to cache")
        except Exception as e:
            print(f"Error saving feature cache: {e}")
    
    
    def mark_page_as_crawled(self, url: str, success: bool = True):
        """标记页面为已爬取（仅内存中记录）"""
        self.crawled_pages[url] = success
    
    def _get_page_template_hash(self, html_content: str, url: str) -> str:
        """
        生成页面模板的哈希值，用于识别相似页面结构
        通过标准化内容来实现泛化能力，相同类型的页面会生成相同的哈希
        
        Args:
            html_content: HTML内容
            url: 页面URL
            
        Returns:
            str: 模板哈希值
        """
        # 1. 提取HTML结构骨架（移除动态内容）
        try:
            from lxml import html
            tree = html.fromstring(html_content)
            
            # 移除脚本和样式标签
            for elem in tree.xpath('//script | //style | //noscript'):
                elem.getparent().remove(elem)
            
            # 标准化动态内容
            template_html = html.tostring(tree, encoding='unicode', method='html')
            
        except Exception:
            # 如果HTML解析失败，使用原始内容
            template_html = html_content
        
        # 2. 内容标准化处理
        template_content = template_html
        
        # 移除或标准化动态内容
        # 日期格式标准化
        template_content = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', 'DATE_PLACEHOLDER', template_content)
        template_content = re.sub(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', 'DATE_PLACEHOLDER', template_content)
        template_content = re.sub(r'\b\d{1,2}:\d{2}(:\d{2})?\b', 'TIME_PLACEHOLDER', template_content)
        
        # 数字标准化
        template_content = re.sub(r'\b\d+\b', 'NUMBER_PLACEHOLDER', template_content)
        
        # URL标准化
        template_content = re.sub(r'https?://[^\s"]+', 'URL_PLACEHOLDER', template_content)
        
        # 邮箱标准化
        template_content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'EMAIL_PLACEHOLDER', template_content)
        
        # 电话号码标准化
        template_content = re.sub(r'\b(?:\+?86)?1[3-9]\d{9}\b', 'PHONE_PLACEHOLDER', template_content)
        template_content = re.sub(r'\b\d{3}-\d{4}-\d{4}\b', 'PHONE_PLACEHOLDER', template_content)
        
        # 价格标准化
        template_content = re.sub(r'\$\d+(?:\.\d+)?', 'PRICE_PLACEHOLDER', template_content)
        template_content = re.sub(r'\d+(?:\.\d+)?\s*(?:USD|EUR|CNY|元|¥|\$)', 'PRICE_PLACEHOLDER', template_content)
        
        # 3. 结构特征提取
        # 提取标签结构模式
        tag_pattern = re.findall(r'<([a-zA-Z][a-zA-Z0-9]*)', template_content)
        tag_sequence = '_'.join(tag_pattern[:50])  # 取前50个标签
        
        # 提取class和id属性模式
        class_pattern = re.findall(r'class\s*=\s*["\']([^"\']+)["\']', template_content)
        id_pattern = re.findall(r'id\s*=\s*["\']([^"\']+)["\']', template_content)
        
        class_sequence = '_'.join([cls for cls_list in class_pattern for cls in cls_list.split()][:20])
        id_sequence = '_'.join(id_pattern[:10])
        
        # 4. 组合URL特征
        url_features = self._extract_url_features(url)
        
        # 5. 生成最终模板
        combined_template = f"{tag_sequence}|{class_sequence}|{id_sequence}|{url_features}"
        
        # 6. 生成哈希
        return hashlib.md5(combined_template.encode('utf-8')).hexdigest()[:16]
    
    def _extract_url_features(self, url: str) -> str:
        """从URL中提取结构化特征"""
        if not url:
            return ""
            
        parsed = urlparse(url.lower())
        domain = parsed.netloc
        
        # 提取路径结构（保留目录层级，但标准化具体名称）
        path_parts = parsed.path.strip('/').split('/')
        path_structure = []
        
        for part in path_parts:
            if not part:
                continue
            # 标准化数字ID
            if part.isdigit():
                path_structure.append('ID')
            # 标准化UUID
            elif re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', part):
                path_structure.append('UUID')
            # 标准化日期
            elif re.match(r'^\d{4}-\d{2}-\d{2}$', part):
                path_structure.append('DATE')
            # 保留关键词
            elif any(kw in part for kw in ['faq', 'help', 'support', 'question', 'answer', 'guide', 'tutorial']):
                path_structure.append(part)
            # 其他部分用GENERIC标记
            else:
                path_structure.append('GENERIC')
        
        path_struct = '/'.join(path_structure)
        
        # 提取查询参数结构
        query_params = []
        if parsed.query:
            params = parsed.query.split('&')
            for param in params:
                if '=' in param:
                    key, _ = param.split('=', 1)
                    query_params.append(key)
                else:
                    query_params.append(param)
        
        query_struct = ','.join(sorted(query_params)) if query_params else ''
        
        return f"{domain}|{path_struct}|{query_struct}"
    
    def _extract_links_from_html(self, html_content: str, base_url: str) -> List[str]:
        """
        从HTML内容中提取所有有效的链接
        """
        links = []
        try:
            from lxml import html
            tree = html.fromstring(html_content)
            
            # 提取所有a标签的href属性
            for elem in tree.xpath('//a[@href]'):
                href = elem.get('href', '').strip()
                if not href:
                    continue
                    
                # 跳过无效链接
                if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                    continue
                    
                try:
                    absolute_url = urljoin(base_url, href)
                    if urlparse(absolute_url).netloc == urlparse(base_url).netloc:
                        if any(keyword in absolute_url.lower() for keyword in ['faq', 'question', 'answer', 'help', 'support']):
                            links.append(absolute_url)
                        elif len(links) < 10:
                            links.append(absolute_url)
                except Exception:
                    continue
        except Exception as e:
            print(f"Error parsing HTML for link extraction: {e}")
            # 如果HTML解析失败，回退到正则表达式方法
            link_pattern = r'<a[^>]+href\s*=\s*["\']([^"\']+)["\'][^>]*>'
            matches = re.findall(link_pattern, html_content, re.IGNORECASE)
            
            for href in matches:
                if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                    continue
                    
                try:
                    absolute_url = urljoin(base_url, href)
                    if urlparse(absolute_url).netloc == urlparse(base_url).netloc:
                        if any(keyword in absolute_url.lower() for keyword in ['faq', 'question', 'answer', 'help', 'support']):
                            links.append(absolute_url)
                        elif len(links) < 10:
                            links.append(absolute_url)
                except Exception:
                    continue
        
        return list(set(links))
    
    def _extract_links_from_markdown(self, markdown_content: str, base_url: str) -> List[str]:
        """
        从Markdown内容中提取所有有效的链接
        """
        links = []
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(link_pattern, markdown_content)
        
        for text, href in matches:
            if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue
                
            try:
                absolute_url = urljoin(base_url, href)
                if urlparse(absolute_url).netloc == urlparse(base_url).netloc:
                    if any(keyword in absolute_url.lower() for keyword in ['faq', 'question', 'answer', 'help', 'support']):
                        links.append(absolute_url)
                    elif len(links) < 10:
                        links.append(absolute_url)
            except Exception:
                continue
                
        return list(set(links))
    
    async def _extract_qa_from_page(self, html_content: str, markdown_content: str, url: str, seed_url: str) -> List[Dict]:
        """
        从页面中提取Q&A数据，使用特征缓存机制
        """
        # 检查是否已经爬取过该页面
        if url in self.crawled_pages:
            print(f"Skipping already crawled page: {url}")
            return []
        
        template_hash = self._get_page_template_hash(html_content, url)
        
        # 检查是否有缓存的特征
        if template_hash in self.feature_cache:
            features = self.feature_cache[template_hash]
            print(f"Using cached features for {url} (template hash: {template_hash})")
            
            # 如果特征标记为跳过（非Q&A页面）
            if features.get('skip', False):
                print(f"Skipping non-Q&A page: {url}")
                self.mark_page_as_crawled(url, success=False)
                return []
            
            # 使用缓存的特征提取Q&A
            qa_data = extract_qa_using_features(html_content, features)
            self.mark_page_as_crawled(url, success=True)
            return [{'seed_url': seed_url, 'url': url, 'question': item['question'], 'answer': item['answer']} 
                   for item in qa_data if item.get('question') and item.get('answer')]
        
        # 没有缓存特征，直接使用大模型提取Q&A内容
        print(f"No cached features for {url} (template hash: {template_hash}), using LLM to extract Q&A directly...")
        return await self._extract_with_llm_and_cache_features(html_content, markdown_content, url, seed_url, template_hash)
    
    async def _extract_with_llm_and_cache_features(self, html_content: str, markdown_content: str, url: str, seed_url: str, template_hash: str) -> List[Dict]:
        """
        直接使用大模型提取Q&A内容，并根据结果反向生成特征
        优先使用大模型返回的选择器信息，如果没有则回退到特征提取器
        """
        # 直接使用大模型提取Q&A内容（现在包含选择器信息）
        qa_pairs = extract_qa_content_with_llm(html_content, url)
        
        if not qa_pairs:
            # 没有提取到Q&A内容，认为是非Q&A页面
            self.feature_cache[template_hash] = {'skip': True}
            self.save_feature_cache()
            self.mark_page_as_crawled(url, success=False)
            print(f"No Q&A content extracted from {url}, marked as non-Q&A page")
            return []
        
        # 首先尝试使用大模型返回的选择器信息构建特征
        features = None
        has_selector_info = any('question_selectors' in pair or 'answer_selectors' in pair for pair in qa_pairs)
        
        if has_selector_info:
            # 从Q&A对中收集选择器信息
            question_selectors = set()
            answer_selectors = set()
            
            for pair in qa_pairs:
                if 'question_selectors' in pair:
                    question_selectors.update(pair['question_selectors'])
                if 'answer_selectors' in pair:
                    answer_selectors.update(pair['answer_selectors'])
            
            if question_selectors or answer_selectors:
                features = {
                    'type': 'css_selector',
                    'question_selector': list(question_selectors) if question_selectors else ['h1', 'h2', 'h3', 'h4'],
                    'answer_selector': list(answer_selectors) if answer_selectors else ['p', '.article-body'],
                    'match_strategy': 'sequential'
                }
                
                # 添加URL模式
                if url:
                    features['url_patterns'] = PageFeatureExtractor._extract_url_patterns(url)
                print(f"Using LLM-provided selectors for {url}")
        
        # 如果没有从LLM获取到选择器信息，则使用特征提取器
        if features is None:
            features = PageFeatureExtractor.extract_features_from_qa_results(html_content, qa_pairs, url)
        
        if features:
            # 缓存特征
            self.feature_cache[template_hash] = features
            self.save_feature_cache()
            print(f"Cached features for {url} (template hash: {template_hash})")
            
            # 标记页面为已爬取
            self.mark_page_as_crawled(url, success=True)
            
            # 返回提取的Q&A数据（只包含question和answer字段）
            return [{'seed_url': seed_url, 'url': url, 'question': item['question'], 'answer': item['answer']} 
                   for item in qa_pairs if item.get('question') and item.get('answer')]
        else:
            # 无法生成特征，但有Q&A内容，直接返回
            print(f"Could not generate features for {url}, but returning extracted Q&A")
            self.mark_page_as_crawled(url, success=True)
            return [{'seed_url': seed_url, 'url': url, 'question': item['question'], 'answer': item['answer']} 
                   for item in qa_pairs if item.get('question') and item.get('answer')]
    
    def _extract_qa_with_heuristics(self, content: str) -> List[Dict]:
        """
        使用启发式规则提取Q&A（备用方案）
        """
        qa_pairs = []
        
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
                
            if line.endswith('?') or any(keyword in line.lower() for keyword in ['how', 'what', 'why', 'when', 'where', 'who', 'can', 'do', 'does']):
                question = line
                answer_lines = []
                j = i + 1
                while j < len(lines) and len(answer_lines) < 5:
                    next_line = lines[j].strip()
                    if next_line and not next_line.endswith('?') and not any(kw in next_line.lower() for kw in ['how', 'what', 'why', 'when', 'where', 'who']):
                        answer_lines.append(next_line)
                        j += 1
                    else:
                        break
                
                if answer_lines:
                    answer = ' '.join(answer_lines)
                    if question and answer and len(question) > 5 and len(answer) > 10:
                        qa_pairs.append({
                            'question': question,
                            'answer': answer
                        })
                        i = j
                    else:
                        i += 1
                else:
                    i += 1
            else:
                i += 1
        
        return qa_pairs
    
    async def crawl_single_page(self, url: str, depth: int = 0, seed_url: str = None) -> List[Dict]:
        """
        爬取单个页面并返回Q&A数据
        """
        # 检查是否已停止
        if self.stopped:
            return []
            
        if seed_url is None:
            seed_url = url
            
        if url in self.visited_urls or url in self.crawled_pages:
            return []
            
        print(f"{'  ' * depth} Crawling: {url} (depth: {depth})")
        self.visited_urls.add(url)
        
        try:
            crawler = await self.get_crawler()
            result = await crawler.arun(
                url=url,
                config=self.crawler_config
            )
            
            if not result or not result.html:
                print(f"{'  ' * depth} No HTML content extracted from {url}")
                self.mark_page_as_crawled(url, success=False)
                return []
            
            # 提取Q&A数据（使用特征缓存机制）
            qa_data = await self._extract_qa_from_page(result.html, result.markdown, url, seed_url)
            if qa_data:
                print(f"{'  ' * depth} Extracted {len(qa_data)} Q&A pairs from {url}")
            
            return qa_data
                
        except Exception as e:
            print(f"{'  ' * depth} Error crawling {url}: {str(e)}")
            self.mark_page_as_crawled(url, success=False)
            # 调用错误回调
            try:
                await self.callback.error(e, url)
            except Exception as callback_error:
                print(f"Error in error callback: {callback_error}")
            return []

    async def crawl(self, seed_url: str, depth: int = 0, original_seed_url: str = None) -> None:
        """
        主爬虫函数，支持递归下钻
        """
        # 检查是否已停止
        if self.stopped:
            return
            
        if original_seed_url is None:
            original_seed_url = seed_url
            
        if depth > self.max_depth:
            return
            
        if seed_url in self.visited_urls:
            return
            
        # 检查是否已经爬取过该页面
        if seed_url in self.crawled_pages:
            print(f"{'  ' * depth} Skipping already crawled page: {seed_url}")
            return
            
        # 爬取当前页面，使用original_seed_url作为种子URL
        try:
            qa_data = await self.crawl_single_page(seed_url, depth, original_seed_url)
            if qa_data:
                # 实时去重：避免将重复的Q&A添加到 extracted_data 中
                unique_qa_data = []
                seen_pairs = set()
                for item in qa_data:
                    pair_key = (item['question'], item['answer'])
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        unique_qa_data.append(item)
                
                if unique_qa_data:
                    self.extracted_data.extend(unique_qa_data)
                    print(f"{'  ' * depth} Added {len(unique_qa_data)} unique Q&A pairs from {seed_url}")
        except Exception as e:
            # 调用错误回调
            try:
                await self.callback.error(e, seed_url)
            except Exception as callback_error:
                print(f"Error in error callback: {callback_error}")
            return

        # 如果还没达到最大深度且未停止，继续下钻
        if depth < self.max_depth and not self.stopped:
            try:
                # 获取当前页面的链接
                crawler = await self.get_crawler()
                result = await crawler.arun(
                    url=seed_url,
                    config=self.crawler_config
                )
                
                if result and result.html:
                    links = self._extract_links_from_html(result.html, seed_url)
                    # 过滤未访问的链接
                    new_links = [link for link in links if link not in self.visited_urls and link not in self.crawled_pages]
                    
                    if new_links:
                        # 并发爬取下一层链接
                        semaphore = asyncio.Semaphore(self.concurrency)
                        
                        async def crawl_with_semaphore(link):
                            if not self.stopped:
                                async with semaphore:
                                    await self.crawl(link, depth + 1, original_seed_url)
                        
                        tasks = [crawl_with_semaphore(link) for link in new_links[:20]]  # 限制每层最多20个链接
                        await asyncio.gather(*tasks)
            except Exception as e:
                # 调用错误回调
                try:
                    await self.callback.error(e, seed_url)
                except Exception as callback_error:
                    print(f"Error in error callback: {callback_error}")
                return
    
    async def run(self, seed_urls: List[str]) -> None:
        """
        运行爬虫
        """
        print(f"Starting crawl with max depth: {self.max_depth}, concurrency: {self.concurrency}")
        
        # 并发处理种子URL
        semaphore = asyncio.Semaphore(self.concurrency)
        
        async def crawl_seed_with_semaphore(seed_url):
            async with semaphore:
                await self.crawl(seed_url, 0)
        
        try:
            tasks = [crawl_seed_with_semaphore(seed_url) for seed_url in seed_urls]
            await asyncio.gather(*tasks)

            if self.stopped:
                print("Crawl stopped before completion.")
                return
            
            # 在保存文件之前，对extracted_data进行全局去重（仅基于question和answer）
            if self.extracted_data:
                unique_qa = []
                seen_pairs = set()
                for item in self.extracted_data:
                    # 仅基于 (question, answer) 二元组进行去重
                    pair_key = (item['question'], item['answer'])
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        unique_qa.append(item)
                
                # 更新extracted_data为去重后的数据
                self.extracted_data = unique_qa
                print(f"Removed {len(self.extracted_data) - len(unique_qa)} duplicate entries from extracted_data")
            
            # 保存提取的Q&A数据到文件（如果output_file不为None）
            if self.extracted_data and self.output_file is not None:
                self.save_to_file()
            elif self.extracted_data:
                print("Q&A data extracted but no output file specified, skipping file save.")
            else:
                print("No Q&A data extracted, skipping file save.")
            
            # 最终保存缓存
            self.save_feature_cache()
            
            # 准备统计信息
            stats = {
                'total_extracted': len(self.extracted_data),
                'unique_urls_visited': len(self.visited_urls),
                'total_urls_crawled': len(self.crawled_pages),
                'feature_cache_size': len(self.feature_cache)
            }
            
            # 调用完成回调
            try:
                await self.callback.finished(self.extracted_data, stats)
            except Exception as e:
                print(f"Error in finished callback: {e}")
                
        except Exception as e:
            # 调用错误回调
            try:
                await self.callback.error(e)
            except Exception as callback_error:
                print(f"Error in error callback: {callback_error}")
            raise

    def save_to_file(self) -> None:
        """保存提取的数据到JSON文件（如果output_file不为None）"""
        if self.output_file is None:
            return
            
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        
        # 此时extracted_data已经是去重后的数据，直接保存即可
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.extracted_data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved {len(self.extracted_data)} Q&A data entries to {self.output_file}")


async def main():
    """主函数示例"""
    # 示例种子URL（可以根据需要修改）
    seed_urls = [
        "https://help.atome.ph/hc/en-gb/categories/4439682039065-Atome-Card"
        # "https://help.atome.ph/hc/en-gb/articles/42145059939353-Are-there-any-fees-for-transacting-with-QR-Ph#main-content"
    ]
    
    # 创建自定义回调类示例
    class ExampleCallback(CrawlCallback):
        async def finished(self, data, stats=None):
            print(f"Crawling finished! Extracted {len(data)} Q&A pairs")
            if stats:
                print(f"Stats: {stats}")
        
        async def error(self, error, url=None):
            print(f"Error occurred: {error}")
            if url:
                print(f"Error URL: {url}")
        
        async def closed(self):
            print("Crawler closed successfully")
    
    callback = ExampleCallback()
    crawler = QACrawler(max_depth=3, output_file="./data/crawled_qa.json", concurrency=10, callback=callback)
    try:
        await crawler.run(seed_urls)
    finally:
        await crawler.close()


if __name__ == "__main__":
    # 在Windows上使用asyncio需要特别处理
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Crawling interrupted by user")
    except Exception as e:
        print(f"Error during crawling: {e}")
        raise