from langgraph.graph import StateGraph, START, END
from core.robot.state import CustomerServiceRobotState

from langgraph.prebuilt import ToolNode
from core.robot.nodes import (
    load_knowledge_base, judge_question_type, match_kb_node,
    handle_specific_question, handle_invalid_question, handle_system_error,
    auto_fix_error, is_invalid_question_cond, is_specific_question_cond,
    has_error_cond,question_dispatch_cond,call_specific_tool_cond, handle_casual_chat
)

from core.robot.tools import query_bank_card_apply_progress,query_bank_card_trans_fail
from core.common.config import DEFAULT_KNOWLEDGE_BASE_URL, DEFAULT_REPLY_STYLE

# 构建客服AI机器人StateGraph
def build_robot_graph():
    graph = StateGraph(CustomerServiceRobotState)

    # 添加节点
    graph.add_node("load_knowledge_base", load_knowledge_base)
    graph.add_node("judge_question_type", judge_question_type)
    graph.add_node("handle_invalid", handle_invalid_question)
    graph.add_node("handle_specific_question",handle_specific_question)
    graph.add_node("call_specific_tool", ToolNode([query_bank_card_apply_progress,query_bank_card_trans_fail]))
    graph.add_node("handle_general_kb", match_kb_node)
    graph.add_node("handle_system_error", handle_system_error)
    graph.add_node("auto_fix_error", auto_fix_error)
    graph.add_node("handle_casual_chat", handle_casual_chat)

    # 定义节点流转
    graph.add_edge(START, "judge_question_type")

    graph.add_conditional_edges("judge_question_type", question_dispatch_cond, {
        "invalid": "handle_invalid",
        "casual_chat": "handle_casual_chat",
        "general_kb": "handle_general_kb",
        "specific_question": "handle_specific_question"
    })

    # 特定问题处理(ReAct模式)
    graph.add_conditional_edges("handle_specific_question", call_specific_tool_cond, {
        "call_tool": "call_specific_tool",
        "end": END
    })

    graph.add_edge("call_specific_tool","handle_specific_question")

    
    # 特定问题工具调用后判断是否有错误
    # graph.add_conditional_edges("call_specific_tool", has_error_cond, {
    #     "handle_system_error": "handle_system_error",
    #     "auto_fix_error": "auto_fix_error",
    #     "end": END
    # })
    
    # 知识库匹配后判断是否有错误
    # graph.add_conditional_edges("handle_general_kb", has_error_cond, {
    #     "handle_system_error": "handle_system_error",
    #     "auto_fix_error": "auto_fix_error",
    #     "end": END
    # })
    
    # 无效问题处理后结束
    graph.add_edge("handle_invalid", END)
    
    # 闲聊处理后结束
    graph.add_edge("handle_casual_chat", END)
    
    # 错误修复后结束
    # graph.add_edge("auto_fix_error", END)
    
    # 系统故障后结束
    # graph.add_edge("handle_system_error", END)

    # 编译图
    return graph.compile()

# 初始化机器人图
robot_graph = build_robot_graph()

robot_graph.get_graph().print_ascii()

# 机器人调用入口
def robot_invoke(user_id: str, question: str, session_id: str = None, kb_url: str = None, reply_style: str = None):
    from core.common.utils import generate_id, format_time
    from core.common.db import db_execute, db_query
    # 如果提供了session_id，尝试从数据库中读取历史会话
    existing_session = None
    if session_id:
        existing_session = db_query(
            "SELECT context FROM customer_sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id)
        )
    
    # 初始化会话ID
    if not session_id or not existing_session:
        session_id = session_id or generate_id("session")
    
    # 初始化状态
    initial_state = {
        "session_id": session_id,
        "user_id": user_id,
        "question": question,
        "history": [],
        "tool_call_result": None,
        "reply": None,
        "error_feedback": None,
        "reply_style": reply_style or DEFAULT_REPLY_STYLE,
        "is_invalid_question": False,
        "is_system_error": False,
        "specific_question_type": None,
        "fix_desc": None
    }
    
    # 如果存在历史会话，恢复上下文
    if existing_session:
        try:
            import ast
            # 尝试解析存储的上下文
            history = ast.literal_eval(existing_session[0][0])
            if isinstance(history, list):
                initial_state["history"] = history
        except (ValueError, SyntaxError, IndexError):
            # 如果解析失败，保持空的历史记录
            pass
    
    # 运行图
    result = robot_graph.invoke(initial_state)
    # 保存会话记录到数据库
    db_execute(
        "INSERT OR REPLACE INTO customer_sessions (session_id, user_id, create_time, last_msg_time, context, feedback_status) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, user_id, format_time(), format_time(), str(result["history"]), "无" if not result["error_feedback"] else "有")
    )
    return result