from langgraph.graph import StateGraph, END
from core.crawl.state import CrawlState
from core.crawl.nodes import discover_qa_urls_node, parse_and_store_node, should_continue_crawling

def create_crawler_graph():
    """Create the web crawling agent graph"""
    workflow = StateGraph(CrawlState)
    
    # Add nodes
    workflow.add_node("discover", discover_qa_urls_node)
    workflow.add_node("parse", parse_and_store_node)
    
    # Set entry point
    workflow.set_entry_point("discover")
    
    # Add edges with conditional routing
    workflow.add_edge("discover", "parse")
    workflow.add_conditional_edges(
        "parse",
        should_continue_crawling,
        {
            "discover": "discover",
            "end": END
        }
    )
    
    return workflow.compile()

# Create the graph instance
crawler_graph = create_crawler_graph()