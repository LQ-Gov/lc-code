#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试短期记忆功能
"""

from core.robot.graph import robot_graph, robot_invoke

def test_short_term_memory():
    """测试短期记忆功能"""
    print("=== 测试短期记忆功能 ===")
    
    # 第一轮对话
    session_id = "test_session_001"
    user_id = "test_user_001"
    
    print("\n第1轮对话:")
    result1 = robot_invoke(
        user_id=user_id,
        question="你好，我想咨询一下银行卡申请进度",
        session_id=session_id
    )
    print(f"回复: {result1['reply']}")
    print(f"会话ID: {result1['session_id']}")
    print(f"消息历史长度: {len(result1['messages'])}")
    
    # 第二轮对话（使用相同的session_id）
    print("\n第2轮对话:")
    result2 = robot_invoke(
        user_id=user_id,
        question="那我的申请状态怎么样了？",
        session_id=session_id
    )
    print(f"回复: {result2['reply']}")
    print(f"消息历史长度: {len(result2['messages'])}")
    print(f"最后一条消息类型: {type(result2['messages'][-1]).__name__ if result2['messages'] else 'None'}")
    
    # 第三轮对话（使用相同的session_id）
    print("\n第3轮对话:")
    result3 = robot_invoke(
        user_id=user_id,
        question="谢谢你的帮助！",
        session_id=session_id
    )
    print(f"回复: {result3['reply']}")
    print(f"最终消息历史长度: {len(result3['messages'])}")
    
    # 验证InMemorySaver是否正确保存了状态
    print("\n=== 验证InMemorySaver状态 ===")
    config = {"configurable": {"thread_id": session_id}}
    try:
        saved_state = robot_graph.get_state(config)
        if saved_state and saved_state.values:
            print(f"InMemorySaver保存的消息历史长度: {len(saved_state.values.get('messages', []))}")
            print("InMemorySaver状态保存成功！")
        else:
            print("InMemorySaver状态为空")
    except Exception as e:
        print(f"获取InMemorySaver状态失败: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_short_term_memory()