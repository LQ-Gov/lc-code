from typing import TypedDict, List, Optional, Dict, Any,Annotated
from operator import add

class CustomerServiceRobotState(TypedDict):
    """Customer service robot state definition for LangGraph"""
    session_id: str
    user_id: str
    question: str
    history: List[Dict[str, Any]]
    tool_call_result: Optional[Dict[str, Any]]
    call_tool: Optional[Dict[str, Any]]
    reply: Optional[str]
    error_feedback: Optional[Dict[str, Any]]
    auto_fix_result:bool
    feedback_id: Optional[str]
    reply_style: str
    is_invalid_question: bool
    is_system_error: bool
    specific_question_type: Optional[str]
    fix_desc: Optional[str]
    classification:str
    messages: Annotated[list, add]