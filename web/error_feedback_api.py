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
    question: str
    robot_reply: str
    error_type: str
    error_desc: str


class UpdateErrorFeedbackRequest(BaseModel):
    fix_status: str
    error_desc: Optional[str] = None


# 错误反馈响应模型
class ErrorFeedback(BaseModel):
    feedback_id: str
    session_id: str
    question: str
    robot_reply: str
    error_type: str
    error_desc: str
    create_time: str
    fix_status: str
    fix_time: Optional[str]


@ef_router.get("", response_model=dict)
def get_error_feedbacks():
    """
    获取所有错误反馈
    """
    try:
        sql = """
            SELECT feedback_id, session_id, question, robot_reply, 
                   error_type, error_desc, create_time, fix_status, fix_time
            FROM error_feedback
            ORDER BY create_time DESC
        """
        results = db_query(sql)
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
               (feedback_id, session_id, question, robot_reply, error_type, error_desc, create_time, fix_status) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (feedback_id, req.session_id, req.question, req.robot_reply, 
             req.error_type, req.error_desc, current_time, "pending")
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
        
        if req.error_desc:
            # 如果提供了新的错误描述，更新它
            db_execute(
                """UPDATE error_feedback 
                   SET fix_status = ?, error_desc = ?, fix_time = ? 
                   WHERE feedback_id = ?""",
                (req.fix_status, req.error_desc, current_time, feedback_id)
            )
        else:
            # 否则只更新修复状态
            db_execute(
                """UPDATE error_feedback 
                   SET fix_status = ?, fix_time = ? 
                   WHERE feedback_id = ?""",
                (req.fix_status, current_time, feedback_id)
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