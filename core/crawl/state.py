from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

@dataclass
class CrawlState:
    """State for the web crawling agent"""
    seed_url: str
    current_urls: List[str] = field(default_factory=list)
    round_count: int = 0
    max_rounds: int = 2
    parser_scripts: Dict[str, str] = field(default_factory=dict)  # domain -> parser_script
    processed_urls: List[str] = field(default_factory=list)