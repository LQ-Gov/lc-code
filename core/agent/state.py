from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import TypedDict
from typing import List, Dict, Optional, Any
from core.common.config import ROBOT_TEMPLATES

# 元智能体核心状态
class MetaAgentState(TypedDict):
    manager_id: str               # 管理者ID
    gen_id: str                   # 生成记录ID
    user_query: str               # 管理者对话需求
    uploaded_docs: List[str]      # 上传文档路径列表
    doc_contents: List[str]       # 解析后的文档内容
    demand_parse_result: str      # 需求解析结果
    robot_template: str           # 选择的机器人模板
    robot_config: Dict[str, Any]  # 生成的机器人配置
    is_demand_understood: bool    # 是否理解需求
    is_robot_generated: bool      # 是否生成机器人
    verify_result: Optional[str]  # 生成验证结果
    error: Optional[str]          # 生成错误