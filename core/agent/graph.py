from langgraph.graph import StateGraph, START, END
from core.agent.state import DevAgentState
from core.agent.nodes import (
    think_about_question,
    execute_tool_action,
    observe_and_decide,
    generate_final_answer
)

def should_continue(state: DevAgentState) -> str:
    """决定是否继续执行工具调用"""
    if state["is_final_answer"]:
        return "end"
    else:
        return "continue"

def build_dev_agent_graph():
    """构建开发代理的StateGraph"""
    graph = StateGraph(DevAgentState)
    
    # 添加节点
    graph.add_node("think", think_about_question)
    graph.add_node("act", execute_tool_action)
    graph.add_node("observe", observe_and_decide)
    graph.add_node("answer", generate_final_answer)
    
    # 定义工作流
    graph.add_edge(START, "think")
    graph.add_conditional_edges(
        "think",
        should_continue,
        {
            "continue": "act",
            "end": "answer"
        }
    )
    graph.add_edge("act", "observe")
    graph.add_conditional_edges(
        "observe",
        should_continue,
        {
            "continue": "act",  # 可能需要多次工具调用
            "end": "answer"
        }
    )
    graph.add_edge("answer", END)
    
    return graph.compile()

# 初始化开发代理图
dev_agent_graph = build_dev_agent_graph()

def dev_agent_invoke(user_id: str, question: str, session_id: str = None, history: list = None):
    """开发代理调用入口"""
    if session_id is None:
        from core.common.utils import generate_id
        session_id = generate_id("dev_session")
    
    if history is None:
        history = []
    
    initial_state = {
        "session_id": session_id,
        "user_id": user_id,
        "question": question,
        "history": history,
        "tool_call_result": None,
        "call_tool": None,
        "reply": None,
        "messages": [],
        "current_step": "thought",
        "available_tools": [],
        "tool_results": [],
        "thought_process": [],
        "is_final_answer": False
    }
    
    try:
        result = dev_agent_graph.invoke(initial_state)
        return {
            "session_id": result["session_id"],
            "reply": result["reply"],
            "tool_call_result": result["tool_call_result"],
            "thought_process": result["thought_process"],
            "is_final_answer": result["is_final_answer"]
        }
    except Exception as e:
        return {
            "session_id": session_id,
            "reply": f"处理请求时发生错误: {str(e)}",
            "tool_call_result": None,
            "thought_process": [f"错误: {str(e)}"],
            "is_final_answer": True,
            "error": str(e)
        }