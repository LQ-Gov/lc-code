import re
from typing import Dict, List, Optional
from lxml import html
from lxml.html import HtmlComment

class PageFeatureExtractor:
    """
    网页特征提取器
    用于分析网页结构，提取question和answer的位置特征
    特征以dict形式存储，包含CSS选择器、XPath或其他定位信息
    """
    
    @staticmethod
    def extract_features_from_content(html_content: str, url: str = "") -> Optional[Dict]:
        """
        从HTML内容中提取页面特征
        
        Args:
            html_content: HTML内容
            url: 页面URL（可选，用于URL模式匹配）
            
        Returns:
            Dict: 包含特征信息的字典，如果无法提取则返回None
        """
        try:
            tree = html.fromstring(html_content)
            
            # 首先尝试针对特定平台的精确模式
            features = PageFeatureExtractor._try_platform_specific_patterns(tree, html_content, url)
            if features:
                if url:
                    features['url_patterns'] = PageFeatureExtractor._extract_url_patterns(url)
                return features
            
            # 尝试多种常见的Q&A结构模式
            features = PageFeatureExtractor._try_common_patterns(tree, html_content)
            
            if features:
                # 添加URL模式（如果提供了URL）
                if url:
                    features['url_patterns'] = PageFeatureExtractor._extract_url_patterns(url)
                
                return features
                
        except Exception as e:
            print(f"Error extracting features: {e}")
            
        return None
    
    @staticmethod
    def _try_platform_specific_patterns(tree, html_content: str, url: str = "") -> Optional[Dict]:
        """尝试针对特定平台（如Zendesk帮助中心）的精确模式"""
        # 检测Zendesk帮助中心
        if "help." in url.lower() or "hc/" in url.lower():
            # Zendesk帮助中心典型结构
            zendesk_patterns = [
                {
                    'question_selectors': ['.article-title', 'h1.article-title', '.article h1'],
                    'answer_selectors': ['.article-body', '.article-content', '.article-body-content']
                },
                {
                    'question_selectors': ['h1'],
                    'answer_selectors': ['.article-body', '.article-content']
                }
            ]
            
            for pattern in zendesk_patterns:
                question_selectors = pattern['question_selectors']
                answer_selectors = pattern['answer_selectors']
                
                valid_questions = []
                valid_answers = []
                
                for q_selector in question_selectors:
                    try:
                        questions = tree.cssselect(q_selector)
                        if questions:
                            # 更严格的过滤：问题应该包含问号或疑问词，且长度适中
                            filtered_questions = [
                                q for q in questions 
                                if (q.text_content().strip() and 
                                    len(q.text_content().strip()) > 10 and 
                                    len(q.text_content().strip()) < 200 and
                                    (q.text_content().strip().endswith('?') or 
                                     any(kw in q.text_content().lower() for kw in ['how', 'what', 'why', 'when', 'where', 'who', 'can', 'do', 'does', 'is', 'are'])))
                            ]
                            if filtered_questions:
                                valid_questions.extend(filtered_questions)
                    except:
                        continue
                
                for a_selector in answer_selectors:
                    try:
                        answers = tree.cssselect(a_selector)
                        if answers:
                            # 更严格的过滤：答案应该有一定长度，但不能太长（避免包含整个页面）
                            filtered_answers = [
                                a for a in answers 
                                if (a.text_content().strip() and 
                                    len(a.text_content().strip()) > 20 and 
                                    len(a.text_content().strip()) < 2000)
                            ]
                            if filtered_answers:
                                valid_answers.extend(filtered_answers)
                    except:
                        continue
                
                if valid_questions and valid_answers:
                    # 使用更精确的匹配策略：一对一映射
                    return {
                        'type': 'css_selector',
                        'question_selector': question_selectors,
                        'answer_selector': answer_selectors,
                        'match_strategy': 'direct_mapping',
                        'platform': 'zendesk'
                    }
        
        return None
    
    @staticmethod
    def extract_features_from_qa_results(html_content: str, qa_pairs: List[Dict], url: str = "") -> Optional[Dict]:
        """
        从Q&A结果中反向查找HTML标签特征（现在使用纯规则方法，不依赖大模型）
        
        Args:
            html_content: HTML内容
            qa_pairs: Q&A对列表（通过规则方法提取）
            url: 页面URL
            
        Returns:
            Dict: 包含特征信息的字典
        """
        try:
            tree = html.fromstring(html_content)
            
            # 为每个Q&A对查找对应的HTML元素
            question_selectors = []
            answer_selectors = []
            
            for qa_pair in qa_pairs[:3]:  # 只分析前3个Q&A对，避免过度复杂
                question_text = qa_pair.get('question', '').strip()
                answer_text = qa_pair.get('answer', '').strip()
                
                if not question_text or not answer_text:
                    continue
                
                # 查找包含问题文本的HTML元素
                question_elements = PageFeatureExtractor._find_elements_containing_text(tree, question_text)
                answer_elements = PageFeatureExtractor._find_elements_containing_text(tree, answer_text)
                
                if question_elements and answer_elements:
                    # 获取这些元素的共同特征（class、tag等）
                    q_features = PageFeatureExtractor._get_common_features(question_elements)
                    a_features = PageFeatureExtractor._get_common_features(answer_elements)
                    
                    if q_features:
                        question_selectors.extend(q_features)
                    if a_features:
                        answer_selectors.extend(a_features)
            
            # 即使没有找到精确的选择器，也可以尝试基于URL和结构的特征
            if not question_selectors and not answer_selectors:
                # 创建基于HTML结构的后备特征，不依赖大模型
                return PageFeatureExtractor._create_structure_based_features(tree, url)
            
            if question_selectors or answer_selectors:
                # 去重并构建特征字典
                question_selectors = list(set(question_selectors)) if question_selectors else []
                answer_selectors = list(set(answer_selectors)) if answer_selectors else []
                
                # 过滤掉过于通用的选择器
                question_selectors = PageFeatureExtractor._filter_generic_selectors(question_selectors)
                answer_selectors = PageFeatureExtractor._filter_generic_selectors(answer_selectors)
                
                # 如果过滤后还有有效的选择器
                if question_selectors or answer_selectors:
                    features = {
                        'type': 'css_selector',
                        'question_selector': question_selectors,
                        'answer_selector': answer_selectors,
                        'match_strategy': 'sequential'
                    }
                    
                    # 添加URL模式
                    if url:
                        features['url_patterns'] = PageFeatureExtractor._extract_url_patterns(url)
                    
                    return features
                else:
                    # 如果所有选择器都被过滤掉了，使用结构化后备方案
                    return PageFeatureExtractor._create_structure_based_features(tree, url)
                
        except Exception as e:
            print(f"Error extracting features from QA results: {e}")
            
        return None
    
    @staticmethod
    def _filter_generic_selectors(selectors: List[str]) -> List[str]:
        """过滤掉过于通用的选择器，避免提取过多无关内容"""
        generic_tags = {'div', 'span', 'p', 'a', 'li', 'ul', 'ol', 'body', 'html', 'head', 'header', 'footer', 'nav', 'section', 'article', 'main'}
        generic_classes = {'container', 'content', 'wrapper', 'main', 'page', 'site', 'layout'}
        
        filtered = []
        for selector in selectors:
            # 跳过纯标签选择器（除了特定的标题标签）
            if selector in generic_tags and selector not in {'h1', 'h2', 'h3', 'h4', 'dt'}:
                continue
            
            # 跳过过于通用的class选择器
            is_generic = False
            for generic_class in generic_classes:
                if f'.{generic_class}' in selector or f'#{generic_class}' in selector:
                    is_generic = True
                    break
            
            if not is_generic:
                filtered.append(selector)
        
        return filtered if filtered else ['h1', 'h2', 'h3', 'h4']  # 如果全部被过滤，使用标题标签作为后备
    
    @staticmethod
    def _create_structure_based_features(tree, url: str) -> Dict:
        """
        创建基于HTML结构的后备特征，完全不依赖大模型
        """
        # 分析页面结构，寻找可能包含Q&A的区域
        potential_question_tags = ['h1', 'h2', 'h3', 'h4', 'dt', '.title', '.heading', '.question', '.article-title']
        potential_answer_tags = ['p', 'div', 'dd', '.content', '.description', '.answer', '.text', '.article-body', '.article-content']
        
        question_selectors = []
        answer_selectors = []
        
        # 检查潜在的问题选择器
        for selector in potential_question_tags:
            try:
                elements = tree.cssselect(selector)
                if elements:
                    # 更严格的过滤：问题应该包含问号或疑问词，且长度适中
                    valid_elements = [
                        e for e in elements 
                        if (e.text_content().strip() and 
                            len(e.text_content().strip()) > 10 and 
                            len(e.text_content().strip()) < 200 and
                            (e.text_content().strip().endswith('?') or 
                             any(kw in e.text_content().lower() for kw in ['how', 'what', 'why', 'when', 'where', 'who', 'can', 'do', 'does', 'is', 'are'])))
                    ]
                    if valid_elements:
                        question_selectors.append(selector)
            except:
                continue
        
        # 检查潜在的答案选择器
        for selector in potential_answer_tags:
            try:
                elements = tree.cssselect(selector)
                if elements:
                    # 更严格的过滤：答案应该有一定长度，但不能太长
                    valid_elements = [
                        e for e in elements 
                        if (e.text_content().strip() and 
                            len(e.text_content().strip()) > 20 and 
                            len(e.text_content().strip()) < 2000)
                    ]
                    if valid_elements:
                        answer_selectors.append(selector)
            except:
                continue
        
        # 如果找到了任何有效的选择器，返回CSS选择器特征
        if question_selectors or answer_selectors:
            features = {
                'type': 'css_selector',
                'question_selector': question_selectors if question_selectors else ['h1', 'h2', 'h3', 'h4'],
                'answer_selector': answer_selectors if answer_selectors else ['p', '.article-body'],
                'match_strategy': 'sequential'
            }
        else:
            # 最后的后备：基于文本模式
            features = {
                'type': 'text_pattern',
                'fallback_mode': True
            }
        
        if url:
            features['url_patterns'] = PageFeatureExtractor._extract_url_patterns(url)
            
        return features
    
    @staticmethod
    def _find_elements_containing_text(tree, text: str, max_elements: int = 5) -> List:
        """查找包含指定文本的HTML元素"""
        elements = []
        text_lower = text.lower()
        
        # 遍历所有元素，但过滤掉注释节点和其他非元素节点
        for element in tree.iter():
            # 跳过注释节点、处理指令等非标准HTML元素
            if isinstance(element, HtmlComment):
                continue
            
            # 确保元素有text_content方法
            if not hasattr(element, 'text_content'):
                continue
                
            if element.text_content().strip():
                element_text = element.text_content().strip().lower()
                # 改进的文本匹配逻辑：使用模糊匹配
                if PageFeatureExtractor._is_text_similar(text_lower, element_text, threshold=0.7):
                    elements.append(element)
                    if len(elements) >= max_elements:
                        break
        
        # 如果没有找到精确匹配，尝试查找包含部分关键词的元素
        if not elements and len(text_lower) > 20:
            # 提取关键词进行匹配
            keywords = PageFeatureExtractor._extract_keywords(text_lower)
            for element in tree.iter():
                if isinstance(element, HtmlComment):
                    continue
                if not hasattr(element, 'text_content'):
                    continue
                    
                element_text = element.text_content().strip().lower()
                keyword_matches = sum(1 for kw in keywords if kw in element_text)
                if keyword_matches >= min(2, len(keywords)):
                    elements.append(element)
                    if len(elements) >= max_elements:
                        break
        
        return elements
    
    @staticmethod
    def _is_text_similar(text1: str, text2: str, threshold: float = 0.7) -> bool:
        """检查两个文本是否相似（基于子字符串匹配）"""
        if not text1 or not text2:
            return False
            
        # 如果一个文本包含另一个文本的大部分内容
        if len(text1) <= len(text2):
            shorter, longer = text1, text2
        else:
            shorter, longer = text2, text1
            
        # 计算较短文本在较长文本中的匹配比例
        if shorter in longer:
            return True
            
        # 尝试分词匹配
        shorter_words = shorter.split()
        matched_words = sum(1 for word in shorter_words if word in longer)
        similarity = matched_words / len(shorter_words) if shorter_words else 0
        
        return similarity >= threshold
    
    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """从文本中提取关键词"""
        # 移除常见停用词
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'}
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        return list(set(keywords))[:5]  # 返回最多5个关键词
    
    @staticmethod
    def _get_common_features(elements: List) -> List[str]:
        """获取元素的共同CSS选择器特征"""
        selectors = []
        
        # 收集所有可能的选择器
        for element in elements:
            # 1. 基于class的选择器
            if element.get('class'):
                classes = element.get('class').split()
                for cls in classes:
                    if cls.strip() and len(cls.strip()) > 2:  # 忽略太短的class名
                        selectors.append(f'.{cls.strip()}')
            
            # 2. 基于id的选择器
            if element.get('id'):
                id_val = element.get("id").strip()
                if id_val and len(id_val) > 2:  # 忽略太短的id
                    selectors.append(f'#{id_val}')
            
            # 3. 基于tag的选择器
            tag = element.tag
            if tag and tag not in ['div', 'span']:  # div和span太通用，不单独使用
                selectors.append(tag)
            
            # 4. 组合选择器（tag.class）
            if element.get('class') and tag and tag not in ['div', 'span']:
                classes = element.get('class').split()
                for cls in classes:
                    if cls.strip() and len(cls.strip()) > 2:
                        selectors.append(f'{tag}.{cls.strip()}')
            
            # 5. 父元素路径选择器（更具体）
            parent = element.getparent()
            if parent is not None and element.get('class'):
                classes = element.get('class').split()
                for cls in classes:
                    if cls.strip() and len(cls.strip()) > 2:
                        parent_tag = parent.tag if parent.tag else '*'
                        selectors.append(f'{parent_tag} > .{cls.strip()}')
        
        return selectors
    
    @staticmethod
    def _try_common_patterns(tree, html_content: str) -> Optional[Dict]:
        """尝试常见的Q&A页面结构模式"""
        
        # 模式1: FAQ常见结构 - question和answer有特定的class或属性
        patterns = [
            # 常见的class名称模式（更具体）
            {'question_selectors': ['.faq-question', '.question', '[data-type="question"]', '.Question', '.accordion-title', '.article-title', '.section-title', '.heading', '.title'],
             'answer_selectors': ['.faq-answer', '.answer', '[data-type="answer"]', '.Answer', '.accordion-content', '.article-body', '.section-content', '.content', '.description', '.text']},
            
            # 常见的标签结构模式（更保守）
            {'question_selectors': ['h1', 'h2', 'h3', 'h4', 'dt'],
             'answer_selectors': ['p', 'dd', '.article-body', '.content']},
             
            # 基于文本内容的模式
            {'question_selectors': ['*[contains(text(), "?")]'],
             'answer_selectors': ['*']}
        ]
        
        for pattern in patterns:
            question_selectors = pattern['question_selectors']
            answer_selectors = pattern['answer_selectors']
            
            # 测试当前模式是否有效
            valid_questions = []
            valid_answers = []
            
            for q_selector in question_selectors:
                try:
                    questions = tree.cssselect(q_selector)
                    if questions:
                        # 更严格的过滤：问题应该包含问号或疑问词，且长度适中
                        filtered_questions = [
                            q for q in questions 
                            if (q.text_content().strip() and 
                                len(q.text_content().strip()) > 10 and 
                                len(q.text_content().strip()) < 200 and
                                (q.text_content().strip().endswith('?') or 
                                 any(kw in q.text_content().lower() for kw in ['how', 'what', 'why', 'when', 'where', 'who', 'can', 'do', 'does', 'is', 'are'])))
                        ]
                        if filtered_questions:
                            valid_questions.extend(filtered_questions)
                except:
                    continue
            
            for a_selector in answer_selectors:
                try:
                    answers = tree.cssselect(a_selector)
                    if answers:
                        # 更严格的过滤：答案应该有一定长度，但不能太长
                        filtered_answers = [
                            a for a in answers 
                            if (a.text_content().strip() and 
                                len(a.text_content().strip()) > 20 and 
                                len(a.text_content().strip()) < 2000)
                        ]
                        if filtered_answers:
                            valid_answers.extend(filtered_answers)
                except:
                    continue
            
            # 如果找到了有效的question和answer元素
            if valid_questions and valid_answers:
                # 简单匹配：假设顺序对应
                if len(valid_questions) == len(valid_answers):
                    return {
                        'type': 'css_selector',
                        'question_selector': question_selectors,
                        'answer_selector': answer_selectors,
                        'match_strategy': 'sequential'
                    }
                elif len(valid_questions) <= len(valid_answers):
                    # 可能一个question对应多个answers，取前N个
                    return {
                        'type': 'css_selector',
                        'question_selector': question_selectors,
                        'answer_selector': answer_selectors,
                        'match_strategy': 'first_n_answers'
                    }
        
        # 模式2: 基于正则表达式的文本模式
        text_features = PageFeatureExtractor._extract_text_based_features(html_content)
        if text_features:
            return text_features
            
        return None
    
    @staticmethod
    def _extract_text_based_features(html_content: str) -> Optional[Dict]:
        """基于文本内容提取特征"""
        lines = html_content.split('\n')
        qa_indicators = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
                
            # 检查是否包含问题关键词或问号
            if (stripped.endswith('?') or 
                any(kw in stripped.lower() for kw in ['how ', 'what ', 'why ', 'when ', 'where ', 'who ', 'can ', 'do ', 'does ', 'is ', 'are '])):
                qa_indicators.append({
                    'line_index': i,
                    'type': 'question'
                })
            # 检查是否包含答案关键词
            elif any(kw in stripped.lower() for kw in ['answer:', 'response:', 'solution:', 'reply:', 'result:']):
                qa_indicators.append({
                    'line_index': i,
                    'type': 'answer_marker'
                })
        
        if qa_indicators:
            return {
                'type': 'text_pattern',
                'qa_indicators': qa_indicators,
                'content_lines': len(lines)
            }
            
        return None
    
    @staticmethod
    def _extract_url_patterns(url: str) -> List[str]:
        """从URL中提取模式特征"""
        patterns = []
        url_lower = url.lower()
        
        # 提取域名
        if '://' in url_lower:
            domain = url_lower.split('://')[1].split('/')[0]
            patterns.append(domain)
        
        # 提取路径中的关键词
        path_keywords = ['faq', 'help', 'support', 'question', 'answer', 'article', 'guide', 'tutorial', 'knowledge', 'info']
        for keyword in path_keywords:
            if keyword in url_lower:
                patterns.append(keyword)
                
        return patterns


def extract_qa_using_features(html_content: str, features: Dict) -> List[Dict]:
    """
    使用特征信息从HTML内容中提取Q&A数据
    
    Args:
        html_content: HTML内容
        features: 特征字典
        
    Returns:
        List[Dict]: Q&A数据列表
    """
    try:
        tree = html.fromstring(html_content)
        qa_pairs = []
        
        if features['type'] == 'css_selector':
            return _extract_by_css_selectors(tree, features)
        elif features['type'] == 'text_pattern':
            return _extract_by_text_patterns(html_content, features)
        else:
            # 对于未知特征类型，使用启发式规则作为最后的后备
            return _extract_by_heuristics(html_content)
            
    except Exception as e:
        print(f"Error extracting QA using features: {e}")
        # 出错时使用启发式规则作为后备
        return _extract_by_heuristics(html_content)


def _extract_by_css_selectors(tree, features: Dict) -> List[Dict]:
    """使用CSS选择器提取Q&A"""
    qa_pairs = []
    
    # 收集所有可能的questions和answers
    all_questions = []
    all_answers = []
    
    for q_selector in features['question_selector']:
        try:
            questions = tree.cssselect(q_selector)
            # 应用更严格的过滤
            filtered_questions = [
                q for q in questions 
                if (q.text_content().strip() and 
                    len(q.text_content().strip()) > 10 and 
                    len(q.text_content().strip()) < 200)
            ]
            all_questions.extend(filtered_questions)
        except:
            continue
            
    for a_selector in features['answer_selector']:
        try:
            answers = tree.cssselect(a_selector)
            # 应用更严格的过滤
            filtered_answers = [
                a for a in answers 
                if (a.text_content().strip() and 
                    len(a.text_content().strip()) > 20 and 
                    len(a.text_content().strip()) < 2000)
            ]
            all_answers.extend(filtered_answers)
        except:
            continue
    
    # 根据匹配策略组合
    if features.get('match_strategy') == 'direct_mapping':
        # 直接映射：通常只有一个问题和一个答案
        if all_questions and all_answers:
            question_text = all_questions[0].text_content().strip()
            answer_text = all_answers[0].text_content().strip()
            if question_text and answer_text:
                qa_pairs.append({
                    'question': question_text,
                    'answer': answer_text
                })
    elif features.get('match_strategy') == 'sequential':
        min_len = min(len(all_questions), len(all_answers))
        for i in range(min_len):
            question_text = all_questions[i].text_content().strip()
            answer_text = all_answers[i].text_content().strip()
            if question_text and answer_text:
                qa_pairs.append({
                    'question': question_text,
                    'answer': answer_text
                })
    elif features.get('match_strategy') == 'first_n_answers':
        for i, question in enumerate(all_questions):
            if i < len(all_answers):
                question_text = question.text_content().strip()
                answer_text = all_answers[i].text_content().strip()
                if question_text and answer_text:
                    qa_pairs.append({
                        'question': question_text,
                        'answer': answer_text
                    })
                    
    return qa_pairs


def _extract_by_text_patterns(html_content: str, features: Dict) -> List[Dict]:
    """使用文本模式提取Q&A"""
    qa_pairs = []
    lines = html_content.split('\n')
    qa_indicators = features['qa_indicators']
    
    i = 0
    while i < len(qa_indicators):
        indicator = qa_indicators[i]
        if indicator['type'] == 'question':
            question_line = lines[indicator['line_index']].strip()
            # 寻找下一个answer或下一段落
            answer_lines = []
            j = indicator['line_index'] + 1
            while j < len(lines) and len(answer_lines) < 5:
                next_line = lines[j].strip()
                if next_line:
                    # 检查是否是新的问题
                    if (next_line.endswith('?') or 
                        any(kw in next_line.lower() for kw in ['how ', 'what ', 'why ', 'when ', 'where ', 'who '])):
                        break
                    answer_lines.append(next_line)
                j += 1
                
            if answer_lines:
                answer_text = ' '.join(answer_lines)
                if question_line and answer_text and len(question_line) > 10 and len(answer_text) > 20:
                    qa_pairs.append({
                        'question': question_line,
                        'answer': answer_text
                    })
        i += 1
        
    return qa_pairs


def _extract_by_heuristics(html_content: str) -> List[Dict]:
    """使用启发式规则作为最后的后备"""
    qa_pairs = []
    
    # 尝试从HTML中提取文本内容
    try:
        tree = html.fromstring(html_content)
        text_content = tree.text_content()
    except:
        text_content = html_content
    
    lines = text_content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        if (line.endswith('?') or 
            any(keyword in line.lower() for keyword in ['how ', 'what ', 'why ', 'when ', 'where ', 'who ', 'can ', 'do ', 'does ', 'is ', 'are '])):
            question = line
            answer_lines = []
            j = i + 1
            while j < len(lines) and len(answer_lines) < 5:
                next_line = lines[j].strip()
                if next_line and not next_line.endswith('?') and not any(kw in next_line.lower() for kw in ['how ', 'what ', 'why ', 'when ', 'where ', 'who ']):
                    answer_lines.append(next_line)
                    j += 1
                else:
                    break
            
            if answer_lines:
                answer = ' '.join(answer_lines)
                if question and answer and len(question) > 10 and len(answer) > 20:
                    qa_pairs.append({
                        'question': question,
                        'answer': answer
                    })
        i += 1
        
    return qa_pairs