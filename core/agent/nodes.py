from core.agent.state import DevAgentState
from core.common.utils import generate_id
from typing import Dict, Any, List, Optional
import json
from core.common.qwen_utils import get_qwen_model
from langchain_core.messages import AIMessage,SystemMessage, ToolMessage, HumanMessage
from core.agent.tools import (
    get_all_knowledge_bases,
    get_current_knowledge_base_url,
    get_enabled_special_question_flows,
    get_specific_question_flow,
    create_knowledge_base,
    update_knowledge_base,
    delete_knowledge_base,
    rebuild_knowledge_base,
    rebuild_current_knowledge_base,
    get_knowledge_base_by_id,
    get_all_special_question_flows,
    create_special_question_flow,
    update_special_question_flow,
    delete_special_question_flow,
    format_special_questions_for_prompt,
    navigate_to_page,
    refresh_page,
    search_document_collection
)

tools = {
    "get_all_knowledge_bases": get_all_knowledge_bases,
    "get_current_knowledge_base_url": get_current_knowledge_base_url,
    "get_knowledge_base_by_id": get_knowledge_base_by_id,
    "create_knowledge_base": create_knowledge_base,
    "update_knowledge_base": update_knowledge_base,
    "delete_knowledge_base": delete_knowledge_base,
    "rebuild_knowledge_base": rebuild_knowledge_base,
    "rebuild_current_knowledge_base": rebuild_current_knowledge_base,
    "get_enabled_special_question_flows": get_enabled_special_question_flows,
    "get_specific_question_flow": get_specific_question_flow,
    "get_all_special_question_flows": get_all_special_question_flows,
    "create_special_question_flow": create_special_question_flow,
    "update_special_question_flow": update_special_question_flow,
    "delete_special_question_flow": delete_special_question_flow,
    "format_special_questions_for_prompt": format_special_questions_for_prompt,
    "navigate_to_page": navigate_to_page,
    "refresh_page": refresh_page,
    "search_document_collection": search_document_collection
}

tool_function_list = tools.values()

def think_about_question(state: DevAgentState) -> DevAgentState:
    """思考阶段：分析用户问题并决定是否需要调用工具"""
    messages = state['messages']

    if state["action"] == "upload_file":
        return {"messages":[AIMessage(content="请描述具体需求")]}
    
    # 如果messages为空，说明是初始状态，需要从question字段获取用户输入
    if not messages:
        user_message = HumanMessage(content=state["question"])
        messages_to_send = [user_message]
    else:
        # 如果messages不为空，使用最后一条消息作为用户输入
        user_message = messages[-1]
        messages_to_send = messages
    
    # 调用大模型判断是否需要工具调用
    model = get_qwen_model()
    model = model.bind_tools(tool_function_list)

    
    prompt = f"""You are an intelligent development assistant helping users modify their customer service chatbot.
The current page displayed in the frontend is: {state['current_preview_url']}

Your tasks are:
1. Determine if you need to call page navigation or page refresh tools based on the user's question
2. Check if you need to read uploaded files, as the user's question may depend on previously uploaded files. If you need to depend on uploaded files, you can search through the vector database. The current collection of uploaded files is available: {state['file_collection_name']}.
3. Decide whether to call other tools to perform operations
4. If the current request is not supported, output "Current operation is not supported"
"""
    
    
    response = model.invoke([*messages_to_send, SystemMessage(content=prompt)])

    return {"messages":[response]}
        

def observe_and_decide(state: DevAgentState) -> Dict[str, Any]:
    """观察工具调用结果并通过大模型判断当前客服机器人状态是否满足用户需求"""
    messages = state['messages']
    
    # 调用大模型分析工具调用结果
    model = get_qwen_model()
    model = model.bind_tools(tool_function_list)
    
    # 构建系统提示词，指导大模型分析当前状态
    prompt = """You are an intelligent development assistant helping users modify their customer service chatbot.
Your task is to analyze the tool execution results and determine if the current chatbot state satisfies the user's requirements.

Please consider:
1. Review the tool execution results carefully
2. Determine if the user's original request has been fully addressed
3. If more actions are needed, decide what specific tools should be called next
4. If the request is complete, provide a final response to the user

Remember to use available tools when additional information or actions are required."""
    
    # 调用大模型进行分析和决策
    response = model.invoke([*messages, SystemMessage(content=prompt)])
    
    # 根据 LangGraph 规范，直接返回新消息
    return {"messages": [response]}

def generate_final_answer(state: DevAgentState) -> DevAgentState:
    """生成最终回答"""
    messages = state['messages']
    
    # 添加安全检查
    if not messages:
        return {"reply": {"type": "message_result", "messages": "抱歉，处理过程中出现了问题。"}}
    
    last = messages[-1]

    if hasattr(last, 'tool_calls') and last.tool_calls:
        return {"messages":[ToolMessage(tool_call_id=last.tool_calls[0]["id"],content="已转发至前端调用")], "reply":{"type":"tool_call_result", "tool_calls":last.tool_calls}}
    
    return {"reply":{"type":"message_result","messages": last.content}}