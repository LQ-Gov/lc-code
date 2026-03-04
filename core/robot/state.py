from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import StateSchema
from typing import List, Dict, Optional, Any,TypedDict
from pydantic import BaseModel

# 工具调用结果模型
class ToolCallResult(BaseModel):
    tool_name: str
    result: Dict[str, Any]
    success: bool
    error: Optional[str] = None

# 错误反馈模型
class ErrorFeedback(BaseModel):
    feedback_id: str
    error_type: str
    error_desc: Optional[str] = None
    fix_status: str = "未修复"

# 客服AI机器人核心状态
class CustomerServiceRobotState(TypedDict):
    session_id: str               # 会话ID
    user_id: str                  # 客户ID
    question: str                 # 客户当前问题
    history: List[Dict]           # 对话历史
    knowledge_base_url: str       # 知识库地址
    knowledge_base_content: str   # 知识库内容
    tool_call_result: Optional[ToolCallResult] # 工具调用结果
    reply: Optional[str]          # 机器人回复
    error_feedback: Optional[ErrorFeedback] # 错误反馈
    reply_style: str              # 回复风格
    is_invalid_question: bool     # 是否为无效问题
    is_system_error: bool         # 是否系统故障