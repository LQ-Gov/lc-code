#!/usr/bin/env python3
"""
Test script for the LangGraph-based customer service robot with Qwen3 integration.
"""

import os
from dotenv import load_dotenv
from core.robot.graph import robot_invoke

# Load environment variables
load_dotenv()

def test_robot_scenarios():
    """Test different customer service scenarios"""
    
    print("=== Testing Customer Service Robot ===\n")
    
    # Test 1: Knowledge base question
    print("1. Testing knowledge base question:")
    result1 = robot_invoke(
        user_id="user_001",
        question="How do I apply for an Atome Card?",
        kb_url=os.getenv("DEFAULT_KNOWLEDGE_BASE_URL")
    )
    print(f"Reply: {result1['reply']}")
    print(f"Error feedback: {result1['error_feedback']}\n")
    
    # Test 2: Bank card application progress
    print("2. Testing bank card application progress:")
    result2 = robot_invoke(
        user_id="user_002",
        question="What is my bank card application progress?"
    )
    print(f"Reply: {result2['reply']}")
    print(f"Tool call result: {result2['tool_call_result']}\n")
    
    # Test 3: Bank card transaction failure (without serial number)
    print("3. Testing bank card transaction failure (no serial number):")
    result3 = robot_invoke(
        user_id="user_003",
        question="My transaction failed, what should I do?"
    )
    print(f"Reply: {result3['reply']}\n")
    
    # Test 4: Invalid question
    print("4. Testing invalid question:")
    result4 = robot_invoke(
        user_id="user_004",
        question="!!!@@@###"
    )
    print(f"Reply: {result4['reply']}\n")
    
    # Test 5: Knowledge base mismatch (should trigger error feedback)
    print("5. Testing knowledge base mismatch:")
    result5 = robot_invoke(
        user_id="user_005",
        question="What is the weather like today?",
        kb_url=os.getenv("DEFAULT_KNOWLEDGE_BASE_URL")
    )
    print(f"Reply: {result5['reply']}")
    print(f"Error feedback: {result5['error_feedback']}\n")

if __name__ == "__main__":
    # Ensure database is initialized
    from core.common.db import init_db
    init_db()
    
    try:
        test_robot_scenarios()
    except Exception as e:
        print(f"Error during testing: {e}")
        print("Make sure you have set your QWEN_API_KEY in the .env file!")