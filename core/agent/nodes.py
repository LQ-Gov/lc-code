from core.agent.state import DevAgentState
from core.common.utils import generate_id
from typing import Dict, Any, List, Optional
import json
from core.common.qwen_utils import get_qwen_model
from langchain_core.messages import AIMessage,SystemMessage

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
    messages = state['messages']
    question = state["messages"][-1].content
    
    # 调用大模型判断是否需要工具调用
    model = get_qwen_model()

    model = model.bind_tools([])

    
    prompt = f"""你是一个智能开发助手，需要根据用户的问题来协助用户修改客服机器人。
    前端展示的当前页面为: {state['current_preview_url']}
    
    你需要:
    1.根据问题判断是否需要调用页面跳转/页面刷新工具
    2.判断是否需要读取文件，用户的问题有部分内容可能依赖之前上传的文件
    3.判断是是否调用其他工具来执行操作
    4.如果用户的当前不支持执行，请输出"当前不支持该操作"
    """
    
    
    response = model.invoke([*messages, SystemMessage(content=prompt)])

    return {"messages":[response]}
        

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
            "action": tool_name,
            "parameters": parameters,
            "status": "success",
            "message": f"成功执行前端工具: {tool_name}"
        }
    elif tool_name in BACKEND_TOOLS:
        result = {
            "tool_type": "backend",
            "action": tool_name,
            "parameters": parameters,
            "status": "success",
            "message": f"成功执行后端工具: {tool_name}"
        }
    else:
        result = {
            "tool_type": "unknown",
            "action": tool_name,
            "parameters": parameters,
            "status": "error",
            "message": f"未知工具: {tool_name}"
        }
    
    return {
        **state,
        "current_step": "observation",
        "tool_call_result": result,
        "tool_results": state["tool_results"] + [result]
    }

def observe_tool_result(state: DevAgentState) -> DevAgentState:
    """观察工具调用结果"""
    tool_call_result = state["tool_call_result"]
    if not tool_call_result:
        return {**state, "current_step": "final_answer", "reply": "工具调用未返回结果。"}
    
    if tool_call_result["status"] == "success":
        # 工具调用成功，生成最终回答
        reply = f"操作成功: {tool_call_result['message']}"
        return {
            **state,
            "current_step": "final_answer",
            "reply": reply,
            "is_final_answer": True
        }
    else:
        # 工具调用失败
        reply = f"操作失败: {tool_call_result['message']}"
        return {
            **state,
            "current_step": "final_answer",
            "reply": reply,
            "is_final_answer": True
        }

def generate_final_answer(state: DevAgentState) -> DevAgentState:
    """生成最终回答"""
    if state["is_final_answer"]:
        if state["reply"]:
            # 如果已经有回复，直接使用
            final_reply = state["reply"]
        elif state["messages"] and hasattr(state["messages"][-1], 'content'):
            # 如果messages中有AI消息，使用最后一条AI消息
            final_reply = state["messages"][-1].content
        else:
            # 默认回复
            final_reply = "我已经处理了您的请求。"
    else:
        # 如果不是最终回答，生成一个默认回复
        final_reply = "处理完成。"
    
    return {
        **state,
        "reply": final_reply,
        "is_final_answer": True
    }