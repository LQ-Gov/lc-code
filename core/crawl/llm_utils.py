import os
import sys
# 添加项目根目录到Python路径，以便能够导入core模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from typing import Dict, List, Optional
from core.common.qwen_utils import get_qwen_model

def is_qa_page_with_llm(content: str) -> bool:
    """
    使用大模型判断页面是否为Q&A页面
    
    Args:
        content: 页面内容
        
    Returns:
        bool: 是否为Q&A页面
    """
    try:
        model = get_qwen_model()
        
        # Use direct model.invoke instead of ChatPromptTemplate (following project specification)
        messages = [
            {"role": "system", "content": "You are an expert at identifying Q&A, FAQ, and help center pages. These pages typically contain questions with corresponding answers, troubleshooting guides, or support documentation."},
            {"role": "user", "content": f"""Analyze the following web page content and determine if it is a Q&A/FAQ/help center page that contains actual questions and their corresponding answers or solutions.

Look for these characteristics:
- Questions ending with '?' or starting with question words (How, What, Why, When, Where, Who, Can, Do, Does, Is, Are)
- Clear answer sections that directly respond to questions
- Help center, support, or FAQ page structure
- Troubleshooting guides with problem-solution format

Content:
{content[:2000]}

Respond with ONLY 'true' or 'false'."""}
        ]
        
        result = model.invoke(messages)
        return result.content.strip().lower() == 'true'
        
    except Exception as e:
        print(f"Error in is_qa_page_with_llm: {e}")
        return False

def extract_qa_content_with_llm(content: str, url: str = "") -> List[Dict]:
    """
    使用大模型直接从页面内容中提取Q&A对和对应的CSS选择器特征
    
    Args:
        content: 页面内容
        url: 页面URL（可选）
        
    Returns:
        List[Dict]: Q&A数据列表，每个包含question、answer和selector_info字段
    """
    try:
        model = get_qwen_model()
        
        # Enhanced prompt specifically designed for help center/FAQ pages
        # Following project specification: use direct model.invoke and English prompts
        messages = [
            {"role": "system", "content": "You are an expert at extracting question-answer pairs from help center and FAQ web pages. Focus on extracting only clear, complete Q&A pairs where both question and answer are present and meaningful. Ignore navigation elements, headers, footers, and unrelated content. Additionally, identify the CSS selectors that can be used to locate these Q&A elements in the HTML structure."},
            {"role": "user", "content": f"""Extract all question-answer pairs from the following help center/FAQ web page content, along with CSS selectors that can be used to locate them.

URL: {url}

Content:
{content[:4000]}

Guidelines for extraction:
1. Look for clear question patterns (ending with '?', starting with 'How', 'What', 'Why', 'When', 'Where', 'Who', 'Can', 'Do', 'Does', 'Is', 'Are')
2. Extract the complete question text exactly as it appears
3. Extract the complete corresponding answer text that directly responds to the question
4. Identify CSS selectors that would uniquely locate the question and answer elements in the HTML
   - For questions: Look for specific class names, IDs, or tag combinations (e.g., '.faq-question', 'h2.article-title', '#main-content h3')
   - For answers: Look for specific class names, IDs, or tag combinations (e.g., '.faq-answer', '.article-body', '#main-content p')
   - If exact selectors cannot be determined, provide the most likely selectors based on common patterns
5. Ignore partial questions, navigation links, table of contents, headers, footers, and unrelated content
6. Ensure both question and answer are substantial (question > 5 characters, answer > 15 characters)
7. For help center articles with a single main question in the title and detailed answer in the body, extract that as one Q&A pair
8. Return only valid Q&A pairs that follow these guidelines

Return the result as a JSON array of objects with 'question', 'answer', and 'selector_info' fields.
The 'selector_info' should be an object with 'question_selectors' and 'answer_selectors' arrays containing CSS selector strings.

Example format:
[{{"question": "What if I am unable to log in to the Atome App?", "answer": "If you are unable to log in to your Atome account, please try the following steps: 1. Check your internet connection...", "selector_info": {{"question_selectors": ["h1.article-title", ".article h1"], "answer_selectors": [".article-body", ".article-content"]}}}}, {{"question": "How do I reset my password?", "answer": "To reset your password, tap on 'Forgot Password' on the login screen...", "selector_info": {{"question_selectors": [".faq-question", "h2"], "answer_selectors": [".faq-answer", ".answer-content"]}}}}]

Return ONLY the JSON array, nothing else."""}
        ]
        
        result = model.invoke(messages)
        
        # 解析JSON结果
        try:
            qa_data = json.loads(result.content.strip())
            # 验证数据格式
            valid_qa = []
            for item in qa_data:
                if isinstance(item, dict) and 'question' in item and 'answer' in item:
                    question = str(item['question']).strip()
                    answer = str(item['answer']).strip()
                    if question and answer and len(question) > 5 and len(answer) > 15:
                        qa_item = {
                            'question': question,
                            'answer': answer
                        }
                        # 提取选择器信息
                        if 'selector_info' in item and isinstance(item['selector_info'], dict):
                            selector_info = item['selector_info']
                            if 'question_selectors' in selector_info:
                                qa_item['question_selectors'] = selector_info['question_selectors']
                            if 'answer_selectors' in selector_info:
                                qa_item['answer_selectors'] = selector_info['answer_selectors']
                        valid_qa.append(qa_item)
            return valid_qa
        except json.JSONDecodeError:
            print("Failed to parse LLM response as JSON")
            return []
            
    except Exception as e:
        print(f"Error in extract_qa_content_with_llm: {e}")
        return []