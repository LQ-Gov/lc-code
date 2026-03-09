from core.crawl.graph import crawler_graph
from core.crawl.state import CrawlState

def run_crawler(seed_url: str, max_rounds: int = 2):
    """Run the web crawler agent with the given seed URL"""
    initial_state = CrawlState(
        seed_url=seed_url,
        max_rounds=max_rounds
    )
    
    result = crawler_graph.invoke(initial_state)
    return result