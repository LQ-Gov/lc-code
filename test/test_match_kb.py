#!/usr/bin/env python3
"""
测试修改后的match_kb_node函数
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.robot.nodes import match_kb_node
from core.robot.state import CustomerServiceRobotState

def test_match_kb_node():
    """测试match_kb_node函数"""
    print("=== 测试match_kb_node函数 ===")
    
    # 测试用例1：关于账单支付的问题（应该能找到匹配）
    test_questions = [
        "如何支付我的账单？",
        "什么时候需要支付账单？",
        "如何重置密码？"  # 这个可能找不到精确匹配
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n--- 测试用例 {i}: {question} ---")
        
        # 创建测试状态
        test_state = CustomerServiceRobotState(
            session_id=f"test_session_{i}",
            user_id="test_user_456",
            question=question,
            knowledge_base_url="https://help.atome.ph/hc/en-gb/categories/4439682039065-Atome-Card",
            reply_style="formal",
            is_invalid_question=False,
            specific_question_type=None,
            classification="general_kb"
        )
        
        try:
            # 调用match_kb_node函数
            result_state = match_kb_node(test_state)
            
            if result_state["reply"]:
                print("✓ 向量库查询成功！")
                print(f"回复预览: {result_state['reply'][:150]}...")
            else:
                print("⚠️ 未找到匹配结果")
                if result_state["error_feedback"]:
                    print(f"错误反馈: {result_state['error_feedback']['error_desc']}")
                    
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_match_kb_node()