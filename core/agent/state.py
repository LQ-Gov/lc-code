from typing import TypedDict, List, Optional, Dict, Any, Annotated
from operator import add

class DevAgentState(TypedDict):
    """Development agent state for ReAct pattern interaction"""
    session_id: str
    user_id: str
    question: str
    action:str
    tool_call_result: Optional[Dict[str, Any]]
    call_tool: Optional[Dict[str, Any]]
    reply: Optional[str]
    messages: Annotated[list, add]
    current_step: str  # "thought", "action", "observation", "final_answer"
    available_tools: List[str]
    tool_results: List[Dict[str, Any]]
    thought_process: List[str]
    is_final_answer: bool
    file_collection_name: Optional[str]
    current_preview_url: Optional[str]
    act_think_cycle_count: int  # Track the number of act-think cycles