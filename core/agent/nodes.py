from core.agent.state import DevAgentState
from core.common.utils import generate_id
from typing import Dict, Any, List, Optional
import json

# 前端工具定义
FRONTEND_TOOLS = {
    "navigate_to_page": {
        "description": "跳转到指定页面",
        "parameters": {"page_url": "目标页面URL", "page_name": "页面名称"}
    },
    "refresh_robot": {
        "description": "刷新客服机器人界面",
        "parameters": {}
    },
    "show_notification": {
        "description": "显示通知消息",
        "parameters": {"message": "通知内容", "type": "通知类型 (info/success/warning/error)"}
    }
}

# 后端工具定义
BACKEND_TOOLS = {
    "add_knowledge_base": {
        "description": "向知识库添加新条目",
        "parameters": {"question": "问题", "answer": "答案", "category": "分类"}
    },
    "delete_knowledge_base": {
        "description": "从知识库删除条目",
        "parameters": {"kb_id": "知识库条目ID"}
    },
    "update_knowledge_base": {
        "description": "更新知识库条目",
        "parameters": {"kb_id": "知识库条目ID", "question": "新问题", "answer": "新答案", "category": "新分类"}
    },
    "add_special_flow": {
        "description": "添加特定流程",
        "parameters": {"flow_name": "流程名称", "steps": "流程步骤列表", "trigger_words": "触发关键词"}
    },
    "delete_special_flow": {
        "description": "删除特定流程",
        "parameters": {"flow_id": "流程ID"}
    },
    "update_special_flow": {
        "description": "更新特定流程",
        "parameters": {"flow_id": "流程ID", "flow_name": "新流程名称", "steps": "新流程步骤", "trigger_words": "新触发关键词"}
    }
}

def get_all_available_tools() -> List[str]:
    """获取所有可用工具列表"""
    return list(FRONTEND_TOOLS.keys()) + list(BACKEND_TOOLS.keys())

def think_about_question(state: DevAgentState) -> DevAgentState:
    """思考阶段：分析用户问题并决定是否需要调用工具"""
    question = state["question"]
    history = state["history"]
    
    # 简化的思考逻辑 - 实际应该使用大模型
    thought = f"用户询问: '{question}'. 需要分析是否需要调用工具来处理此请求。"
    
    # 判断是否需要工具调用
    needs_tool = any(tool in question.lower() for tool in get_all_available_tools())
    
    if needs_tool:
        # 识别可能需要的工具
        possible_tools = []
        for tool in get_all_available_tools():
            if tool.replace('_', ' ') in question.lower() or tool in question.lower():
                possible_tools.append(tool)
        
        if possible_tools:
            next_step = "action"
            call_tool = {"tool_name": possible_tools[0], "parameters": {}}
        else:
            next_step = "final_answer"
            call_tool = None
    else:
        next_step = "final_answer"
        call_tool = None
    
    return {
        **state,
        "current_step": next_step,
        "call_tool": call_tool,
        "thought_process": [thought],
        "is_final_answer": next_step == "final_answer"
    }

def execute_tool_action(state: DevAgentState) -> DevAgentState:
    """执行工具调用"""
    call_tool = state["call_tool"]
    if not call_tool:
        return {**state, "current_step": "observation", "tool_call_result": None}
    
    tool_name = call_tool["tool_name"]
    parameters = call_tool.get("parameters", {})
    
    # 模拟工具执行结果
    if tool_name in FRONTEND_TOOLS:
        result = {
            "tool_type": "frontend",
            "tool_name": tool_name,
            "status": "success",
            "message": f"前端工具 '{tool_name}' 已准备执行",
            "parameters": parameters
        }
    elif tool_name in BACKEND_TOOLS:
        result = {
            "tool_type": "backend",
            "tool_name": tool_name,
            "status": "success",
            "message": f"后端工具 '{tool_name}' 已执行",
            "parameters": parameters
        }
    else:
        result = {
            "tool_type": "unknown",
            "tool_name": tool_name,
            "status": "error",
            "message": f"未知工具: {tool_name}",
            "parameters": parameters
        }
    
    tool_results = state.get("tool_results", []) + [result]
    
    return {
        **state,
        "current_step": "observation",
        "tool_call_result": result,
        "tool_results": tool_results
    }

def observe_and_decide(state: DevAgentState) -> DevAgentState:
    """观察工具执行结果并决定下一步"""
    tool_result = state["tool_call_result"]
    thought_process = state["thought_process"]
    
    if tool_result:
        observation = f"工具执行结果: {tool_result['message']}"
        thought_process.append(observation)
        
        # 如果工具执行成功且是最终操作，则生成最终答案
        if tool_result["status"] == "success":
            final_answer = f"已成功执行操作: {tool_result['message']}"
            return {
                **state,
                "current_step": "final_answer",
                "reply": final_answer,
                "thought_process": thought_process,
                "is_final_answer": True
            }
        else:
            # 工具执行失败，提供错误信息
            error_answer = f"操作失败: {tool_result['message']}"
            return {
                **state,
                "current_step": "final_answer",
                "reply": error_answer,
                "thought_process": thought_process,
                "is_final_answer": True
            }
    else:
        # 没有工具调用，直接生成回答
        simple_answer = f"您的问题是: '{state['question']}'. 这是一个常规问题，不需要特殊工具处理。"
        return {
            **state,
            "current_step": "final_answer",
            "reply": simple_answer,
            "thought_process": thought_process,
            "is_final_answer": True
        }

def generate_final_answer(state: DevAgentState) -> DevAgentState:
    """生成最终答案"""
    if state["is_final_answer"] and state["reply"]:
        return state
    
    # 如果还没有最终答案，生成一个
    if not state["reply"]:
        reply = "已完成处理您的请求。"
        return {**state, "reply": reply, "is_final_answer": True}
    
    return state