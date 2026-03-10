from core.crawl.scripts.base_parser import BaseParser
from bs4 import BeautifulSoup
from typing import List, Dict
import re


class CommunityTopicParser(BaseParser):
    """
    Parser for Zendesk Help Center Community Topic pages.
    Extracts question-answer pairs from community discussion lists.
    """

    def supports(self, url: str, content: str) -> bool:
        """
        Determines if this parser can handle the given URL and content.
        
        Args:
            url: The webpage URL.
            content: The raw HTML content of the page.
            
        Returns:
            True if the page matches the Zendesk Help Center Community structure, False otherwise.
        """
        try:
            if not url or not content:
                return False
            
            # Check domain and path patterns typical for Atome Help Center
            if "help.atome.ph" not in url:
                return False
            
            if "/hc/" not in url:
                return False
            
            # Check for community-specific indicators in URL or content
            if "community" not in url:
                # Fallback to content check if URL is ambiguous but content indicates community
                if "community-enabled" not in content:
                    return False
            
            # Verify Zendesk Help Center specific assets or structure
            if "static.zdassets.com/hc" not in content and "community-enabled" not in content:
                return False
                
            return True
            
        except Exception:
            return False

    def parse(self, url: str, content: str) -> List[Dict[str, str]]:
        """
        Parses question-answer pairs from the community topics page.
        
        Args:
            url: The webpage URL.
            content: The raw HTML content of the page.
            
        Returns:
            A list of dictionaries containing 'question' and 'answer' keys.
        """
        results = []
        
        try:
            if not content:
                return results
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Identify the main list container for community topics
            # Zendesk typically uses .community-topic-list or similar structures
            topic_containers = soup.find_all('li', class_=re.compile(r'community-topic-list-item'))
            
            # If specific class not found, try broader search within community section
            if not topic_containers:
                community_section = soup.find(class_=re.compile(r'community.*list'))
                if community_section:
                    topic_containers = community_section.find_all('li')
            
            for item in topic_containers:
                question_text = ""
                answer_text = ""
                
                # Extract Question (usually the title link)
                title_link = item.find('a', class_=re.compile(r'community-topic-list-item-title'))
                if not title_link:
                    # Fallback: first anchor tag in the item
                    title_link = item.find('a')
                
                if title_link and title_link.get_text(strip=True):
                    question_text = title_link.get_text(strip=True)
                
                # Extract Answer (usually excerpt, meta data, or description)
                # Try specific excerpt class first
                excerpt = item.find(class_=re.compile(r'community-topic-list-item-excerpt'))
                if not excerpt:
                    # Fallback: meta data or description div
                    excerpt = item.find(class_=re.compile(r'meta-data|description|excerpt'))
                
                if excerpt and excerpt.get_text(strip=True):
                    answer_text = excerpt.get_text(strip=True)
                else:
                    # Fallback: Take remaining text content excluding the title
                    # Remove the title link text from the item's total text to get description
                    full_text = item.get_text(separator=' ', strip=True)
                    if question_text and full_text:
                        # Simple removal attempt, might be imperfect but handles cases without explicit excerpt
                        answer_text = full_text.replace(question_text, '', 1).strip()
                
                # Validate non-empty strings for both question and answer
                if question_text and answer_text:
                    # Clean up whitespace and newlines
                    clean_question = re.sub(r'\s+', ' ', question_text)
                    clean_answer = re.sub(r'\s+', ' ', answer_text)
                    
                    results.append({
                        'question': clean_question,
                        'answer': clean_answer
                    })
                    
        except Exception:
            # Return empty list on parsing errors to ensure robustness
            return []
            
        return results