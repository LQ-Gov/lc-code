from fastapi import APIRouter
from pydantic import BaseModel
from core.common.db import db_query, db_execute
from typing import List, Optional
from datetime import datetime


# 创建路由实例
ef_router = APIRouter(prefix="/api/error-feedback", tags=["error_feedback"])

# 错误反馈请求模型
class ErrorFeedbackRequest(BaseModel):
    session_id: str
    user_id: str
    chat_messages: str
    feedback_error_type: str
    feedback_error_detail: str


class UpdateErrorFeedbackRequest(BaseModel):
    auto_fix_result: Optional[str] = None
    status: str
    feedback_error_detail: Optional[str] = None


# 错误反馈响应模型
class ErrorFeedback(BaseModel):
    feedback_id: str
    user_id: str
    session_id: str
    chat_messages: str
    feedback_error_type: str
    feedback_error_detail: str
    auto_fix_result: Optional[str]
    status: str
    create_time: str
    update_time: str


@ef_router.get("", response_model=dict)
def get_error_feedbacks():
    """
    获取所有错误反馈
    """
    try:
        sql = """
            SELECT feedback_id, user_id, session_id, chat_messages, 
                   feedback_error_type, feedback_error_detail, auto_fix_result, status,
                   create_time, update_time
            FROM error_feedback
            ORDER BY create_time DESC
        """
        results = db_query(sql)
        feedbacks = []
        for result in results:
            feedback = {
                "feedback_id": result[0],
                "user_id": result[1],
                "session_id": result[2],
                "chat_messages": result[3],
                "feedback_error_type": result[4],
                "feedback_error_detail": result[5],
                "auto_fix_result": result[6],
                "status": result[7],
                "create_time": result[8],
                "update_time": result[9]
            }
            feedbacks.append(feedback)
        return {"code": 200, "msg": "success", "data": feedbacks}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": []}


@ef_router.post("", response_model=dict)
def create_error_feedback(req: ErrorFeedbackRequest):
    """
    创建错误反馈
    """
    try:
        feedback_id = f"fb_{int(datetime.now().timestamp())}"
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        db_execute(
            """INSERT INTO error_feedback 
               (feedback_id, user_id, session_id, chat_messages, feedback_error_type, 
                feedback_error_detail, auto_fix_result, status, create_time, update_time) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (feedback_id, req.user_id, req.session_id, req.chat_messages, req.feedback_error_type, 
             req.feedback_error_detail, None, "待修复", current_time, current_time)
        )
        return {"code": 200, "msg": "错误反馈创建成功", "data": {"feedback_id": feedback_id}}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}


@ef_router.put("/{feedback_id}", response_model=dict)
def update_error_feedback(feedback_id: str, req: UpdateErrorFeedbackRequest):
    """
    更新错误反馈状态
    """
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if req.feedback_error_detail and req.auto_fix_result:
            # 更新错误描述和自动修复结果
            db_execute(
                """UPDATE error_feedback 
                   SET auto_fix_result = ?, status = ?, feedback_error_detail = ?, update_time = ? 
                   WHERE feedback_id = ?""",
                (req.auto_fix_result, req.status, req.feedback_error_detail, current_time, feedback_id)
            )
        elif req.feedback_error_detail:
            # 只更新错误描述
            db_execute(
                """UPDATE error_feedback 
                   SET status = ?, feedback_error_detail = ?, update_time = ? 
                   WHERE feedback_id = ?""",
                (req.status, req.feedback_error_detail, current_time, feedback_id)
            )
        elif req.auto_fix_result:
            # 只更新自动修复结果
            db_execute(
                """UPDATE error_feedback 
                   SET auto_fix_result = ?, status = ?, update_time = ? 
                   WHERE feedback_id = ?""",
                (req.auto_fix_result, req.status, current_time, feedback_id)
            )
        else:
            # 只更新状态
            db_execute(
                """UPDATE error_feedback 
                   SET status = ?, update_time = ? 
                   WHERE feedback_id = ?""",
                (req.status, current_time, feedback_id)
            )
        
        return {"code": 200, "msg": "错误反馈更新成功", "data": {}}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}


@ef_router.delete("/{feedback_id}", response_model=dict)
def delete_error_feedback(feedback_id: str):
    """
    删除错误反馈
    """
    try:
        db_execute("DELETE FROM error_feedback WHERE feedback_id = ?", (feedback_id,))
        return {"code": 200, "msg": "错误反馈删除成功", "data": {}}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}


@ef_router.get("/by-session/{session_id}", response_model=dict)
def get_error_feedback_by_session(session_id: str):
    """
    根据会话ID获取错误反馈
    """
    try:
        sql = """
            SELECT feedback_id, session_id, question, robot_reply, 
                   error_type, error_desc, create_time, fix_status, fix_time
            FROM error_feedback
            WHERE session_id = ?
            ORDER BY create_time DESC
        """
        results = db_query(sql, (session_id,))
        feedbacks = []
        for result in results:
            feedback = {
                "feedback_id": result[0],
                "session_id": result[1],
                "question": result[2],
                "robot_reply": result[3],
                "error_type": result[4],
                "error_desc": result[5],
                "create_time": result[6],
                "fix_status": result[7],
                "fix_time": result[8]
            }
            feedbacks.append(feedback)
        return {"code": 200, "msg": "success", "data": feedbacks}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": []}