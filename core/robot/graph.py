from langgraph.graph import StateGraph, START, END
from core.robot.state import CustomerServiceRobotState
from core.robot.nodes import (
    load_knowledge_base, judge_question_type, match_kb_node,
    call_specific_tool_node, handle_invalid_question, handle_system_error,
    auto_fix_error, is_invalid_question_cond, is_specific_question_cond,
    has_error_cond
)
from core.common.config import DEFAULT_KNOWLEDGE_BASE_URL, DEFAULT_REPLY_STYLE

# 构建客服AI机器人StateGraph
def build_robot_graph():
    graph = StateGraph(CustomerServiceRobotState)

    # 添加节点
    graph.add_node("load_knowledge_base", load_knowledge_base)
    graph.add_node("judge_question_type", judge_question_type)
    graph.add_node("handle_invalid", handle_invalid_question)
    graph.add_node("call_specific_tool", call_specific_tool_node)
    graph.add_node("match_kb", match_kb_node)
    graph.add_node("handle_system_error", handle_system_error)
    graph.add_node("auto_fix_error", auto_fix_error)

    # 定义节点流转
    graph.add_edge(START, "load_knowledge_base")
    graph.add_edge("load_knowledge_base", "judge_question_type")
    # 条件边：是否无效问题
    graph.add_conditional_edges("judge_question_type", is_invalid_question_cond, {
        "handle_invalid": END,
        "judge_specific": "is_specific_question"
    })
    # 新增中间节点用于条件判断（简化流转）
    graph.add_conditional_edges("judge_question_type", is_specific_question_cond, {
        "call_specific_tool": "call_specific_tool",
        "match_kb": "match_kb"
    })
    # 特定问题工具调用后判断是否有错误
    graph.add_conditional_edges("call_specific_tool", has_error_cond, {
        "handle_system_error": END,
        "auto_fix_error": "auto_fix_error",
        "end": END
    })
    # 知识库匹配后判断是否有错误
    graph.add_conditional_edges("match_kb", has_error_cond, {
        "handle_system_error": END,
        "auto_fix_error": "auto_fix_error",
        "end": END
    })
    # 错误修复后结束
    graph.add_edge("auto_fix_error", END)
    # 系统故障后结束
    graph.add_edge("handle_system_error", END)

    # 编译图
    return graph.compile()

# 初始化机器人图
robot_graph = build_robot_graph()

# 机器人调用入口
def robot_invoke(user_id: str, question: str, session_id: str = None, kb_url: str = None, reply_style: str = None):
    from core.common.utils import generate_id, format_time
    from core.common.db import db_execute
    # 初始化会话ID
    session_id = session_id or generate_id("session")
    # 初始化状态
    initial_state = {
        "session_id": session_id,
        "user_id": user_id,
        "question": question,
        "history": [],
        "knowledge_base_url": kb_url or DEFAULT_KNOWLEDGE_BASE_URL,
        "knowledge_base_content": "",
        "tool_call_result": None,
        "reply": None,
        "error_feedback": None,
        "reply_style": reply_style or DEFAULT_REPLY_STYLE,
        "is_invalid_question": False,
        "is_system_error": False
    }
    # 运行图
    result = robot_graph.invoke(initial_state)
    # 保存会话记录到数据库
    db_execute(
        "INSERT OR REPLACE INTO customer_sessions (session_id, user_id, create_time, last_msg_time, context, feedback_status) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, user_id, format_time(), format_time(), str(result["history"]), "无" if not result["error_feedback"] else "有")
    )
    return result