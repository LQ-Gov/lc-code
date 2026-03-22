from langgraph.graph import StateGraph, START, END
from core.agent.state import DevAgentState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage,SystemMessage, ToolMessage, HumanMessage
from core.agent.nodes import (
    think_about_question,
    doc_search,
    tools,
    observe_and_decide,
    generate_final_answer
)

def should_continue(state: DevAgentState) -> str:
    """决定是否继续执行工具调用"""
    messages = state["messages"]
    # 添加安全检查，确保messages不为空
    if not messages:
        return "end"
    
    
    
    last_message = messages[-1]


    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        call = last_message.tool_calls[0]
        name = call["name"]
        t = tools[name]
        executor = t.extras['executor'] if t.extras else None
        if executor=="frontend":
            return "end"
        else:
            return "continue"
    else:
        return "end"

def build_dev_agent_graph():
    """构建开发代理的StateGraph"""
    graph = StateGraph(DevAgentState)
    
    # 添加节点
    graph.add_node("doc_search", doc_search)
    graph.add_node("think", think_about_question)
    graph.add_node("act", ToolNode(tools.values()))
    graph.add_node("observe", observe_and_decide)
    graph.add_node("answer", generate_final_answer)
    
    # 定义工作流
    graph.add_edge(START, "think")
    # graph.add_edge(START, "doc_search")
    # graph.add_edge("doc_search", "think")
    graph.add_conditional_edges(
        "think",
        should_continue,
        {
            "continue": "act",
            "end": "answer"
        }
    )
    graph.add_edge("act", "think")
    # graph.add_conditional_edges(
    #     "observe",
    #     should_continue,
    #     {
    #         "continue": "act",  # 可能需要多次工具调用
    #         "end": "answer"
    #     }
    # )
    graph.add_edge("answer", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)

# 初始化开发代理图
dev_agent_graph = build_dev_agent_graph()

def dev_agent_invoke(user_id: str, question: str, session_id: str = None, action:str = None, file_collection_name: str = None, current_preview_url: str = None):
    """开发代理调用入口"""
    if session_id is None:
        from core.common.utils import generate_id
        session_id = generate_id("dev_session")
    
    # if history is None:
    #     history = []
    
    # initial_state = {
    #     "session_id": session_id,
    #     "user_id": user_id,
    #     "question": question,
    #     "history": history,
    #     "tool_call_result": None,
    #     "call_tool": None,
    #     "reply": None,
    #     "messages": [],
    #     "current_step": "thought",
    #     "available_tools": [],
    #     "tool_results": [],
    #     "thought_process": [],
    #     "is_final_answer": False,
    #     "file_collection_name": file_collection_name,
    #     "current_preview_url": current_preview_url
    # }

    state = {}
    if file_collection_name:
        state['file_collection_name'] = file_collection_name
    if question:
        state['messages'] = [HumanMessage(content=question)]
    if current_preview_url:
        state['current_preview_url'] = current_preview_url
    
    state['action'] = action
    if user_id:
        state['user_id'] = user_id
    if session_id:
        state['session_id'] = session_id
    # initial_state["messages"].append(HumanMessage(content=question))
    
    try:
        # 使用MemorySaver时，需要传递config参数来指定thread_id
        config = {"configurable": {"thread_id": session_id}}
        latest_state = dev_agent_graph.get_state(config=config)
       
        result = dev_agent_graph.invoke(state, config=config)
        return {
            "session_id": result["session_id"],
            "reply": result["reply"],
            "tool_call_result": result.get("tool_call_result"),
            "thought_process": result.get("thought_process"),
            "is_final_answer": result.get("is_final_answer")
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