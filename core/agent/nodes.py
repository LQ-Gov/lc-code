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

def doc_search(state: DevAgentState) -> DevAgentState:
    """文档搜索节点：如果用户之前上传过文件，则根据用户输入从对应的向量库中进行检索"""
    # 检查是否有上传的文件集合名称
    if state["action"] == "upload_file" or not state.get('file_collection_name'):
        # 如果没有上传文件，直接返回空结果
        return {}

    # 获取用户查询
    # 优先从messages中获取最后一条消息，如果没有则使用question字段
    messages = state.get('messages', [])
    if messages:
        # 获取最后一条消息的内容
        last_message = messages[-1]
        user_query = last_message.content if hasattr(last_message, 'content') else str(last_message)
    else:
        # 如果messages为空，使用question字段
        user_query = state.get("question", "")
    
    if not user_query:
        return {"messages": [AIMessage(content="No query provided for document search.")]}

    # 使用search_document_collection工具进行检索
    try:
        # search_results = search_document_collection.invoke(
        #     collection_name=state['file_collection_name'],
        #     query=user_query,
        #     n_results=5
        # )

        search_results = search_document_collection.invoke({
            "collection_name":state['file_collection_name'],
            "query":"user_query",
            "n_results":2
        })
        
        # 如果搜索结果是错误信息，直接返回错误
        if isinstance(search_results, dict) and "error" in search_results:
            error_message = f"Document search failed: {search_results['error']}"
            return {"messages": [AIMessage(content=error_message)]}
        
        # 格式化搜索结果
        if search_results:
            formatted_results = []
            for i, result in enumerate(search_results[:3]):  # 只取前3个结果
                content = result.get('content', '')
                source = result.get('source', '')
                distance = result.get('distance', 0.0)
                formatted_results.append(f"Result {i+1}:\nContent: {content}\nSource: {source}\nRelevance: {1-distance:.2f}")
            
            search_summary = "Found relevant information in the uploaded document:\n\n" + "\n\n".join(formatted_results)
            return {"messages": [AIMessage(content=search_summary)]}
        else:
            return {}
    except Exception as e:
        error_message = f"Error during document search: {str(e)}"
        return {"messages": [AIMessage(content=error_message)]}


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
The vector database collection name: {state.get('file_collection_name','')}

Your tasks are:
1. Determine if you need to call page navigation or page refresh tools based on the user's question
2. Check if has uploaded files, as the user's question may depend on previously uploaded files. If you need to depend on uploaded files, you can search through the vector database.
3. Decide whether to call other tools to perform operations
4. If the current request is not supported, output "Current operation is not supported"

CRITICAL REQUIREMENT: After modifying any functionality related to knowledge bases, special flows, or error feedback, you MUST navigate to or refresh the corresponding page to ensure the changes are visible to the user. Specifically:
- After knowledge base operations (create, update, delete), navigate to "/admin#knowledge-base"
- After special flow operations (create, update, delete), navigate to "/admin#special-flows"  
- After error feedback operations, navigate to "/admin#error_feedback"
- After robot configuration changes, either navigate to "/robot" or call refresh_page() to refresh the current interface

Always ensure the user can immediately see the results of their requested modifications by using the appropriate navigation or refresh tool.
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