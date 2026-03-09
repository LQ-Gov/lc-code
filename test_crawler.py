#!/usr/bin/env python3
"""
Test script for the web crawler agent

Before running this script, make sure to:
1. Install required dependencies: pip install python-dotenv langchain-openai
2. Set up your .env file with QWEN_API_KEY and QWEN_MODEL_NAME
3. The crawler will use LLM calls to:
   - Determine if pages are QA pages
   - Extract question-answer links
   - Generate parser scripts for different website formats
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from core.crawl import run_crawler

def main():
    # Check if API key is configured
    if not os.getenv("QWEN_API_KEY"):
        print("Error: QWEN_API_KEY not found in .env file")
        print("Please set up your .env file with your Qwen API key")
        return
    
    # Test with a seed URL
    seed_url = "https://example.com/seed-page"
    
    print(f"Starting crawler with seed URL: {seed_url}")
    print("This will use LLM calls to analyze pages and generate parsers...")
    
    try:
        result = run_crawler(seed_url, max_rounds=2)
        
        print("\nCrawling completed!")
        print(f"Total rounds executed: {result.round_count}")
        print(f"Parser scripts cached: {len(result.parser_scripts)}")
        print(f"Processed URLs: {len(result.processed_urls)}")
        
        # Display some results from the database
        from core.common.db import db_execute
        results = db_execute("SELECT current_url, questions, answers FROM crawler_results WHERE seed_url = ?", (result.seed_url,))
        print(f"Database records found: {len(results)}")
        
        for i, result_item in enumerate(results[:2]):  # Show first 2
            print(f"\nResult {i+1}:")
            print(f"  Current URL: {result_item[0]}")
            print(f"  Question: {result_item[1][:100]}...")
            print(f"  Answer: {result_item[2][:100]}...")
            
    except Exception as e:
        print(f"Error during crawling: {e}")
        print("Make sure your Qwen API key is valid and you have internet connectivity")

if __name__ == "__main__":
    main()