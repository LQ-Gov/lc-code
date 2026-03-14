from core.common.utils import generate_id, format_time
from core.common.db import db_execute, db_query
from typing import Optional, Dict, Any


class ErrorFeedbackService:
    """错误反馈服务类，封装所有错误反馈相关的数据库操作"""
    
    # 错误反馈状态枚举
    STATUS_INVALID = "无效"
    STATUS_PENDING = "待修复"
    STATUS_AUTO_FIXED = "已自动修复"
    STATUS_AUTO_FIXED_USER_CONFIRMED = "自动修复_用户反馈正确"
    STATUS_AUTO_FIXED_USER_REJECTED = "自动修复_用户反馈错误"
    STATUS_MANUALLY_CONFIRMED = "人工已确认"
    
    @staticmethod
    def create_error_feedback(
        user_id: str,
        session_id: str,
        chat_messages: str,
        feedback_error_type: str,
        feedback_error_detail: str,
        status: str = "待修复"
    ) -> str:
        """创建错误反馈记录"""
        feedback_id = generate_id("feedback")
        current_time = format_time()
        
        db_execute(
            """INSERT INTO error_feedback 
               (feedback_id, user_id, session_id, chat_messages, feedback_error_type, 
                feedback_error_detail, auto_fix_result, status, create_time, update_time) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (feedback_id, user_id, session_id, chat_messages, feedback_error_type, 
             feedback_error_detail, None, status, current_time, current_time)
        )
        return feedback_id
    
    @staticmethod
    def update_error_feedback(
        feedback_id: str,
        auto_fix_result: Optional[str] = None,
        status: Optional[str] = None,
        feedback_error_detail: Optional[str] = None
    ) -> bool:
        """更新错误反馈记录"""
        current_time = format_time()
        
        # 构建动态更新语句
        set_parts = []
        params = []
        
        if auto_fix_result is not None:
            set_parts.append("auto_fix_result = ?")
            params.append(auto_fix_result)
        
        if status is not None:
            set_parts.append("status = ?")
            params.append(status)
            
        if feedback_error_detail is not None:
            set_parts.append("feedback_error_detail = ?")
            params.append(feedback_error_detail)
            
        set_parts.append("update_time = ?")
        params.append(current_time)
        params.append(feedback_id)
        
        if not set_parts:
            return False
            
        sql = f"UPDATE error_feedback SET {', '.join(set_parts)} WHERE feedback_id = ?"
        db_execute(sql, params)
        return True
    
    @staticmethod
    def get_error_feedback(feedback_id: str) -> Optional[Dict[str, Any]]:
        """获取错误反馈记录"""
        sql = """
            SELECT feedback_id, user_id, session_id, chat_messages, 
                   feedback_error_type, feedback_error_detail, auto_fix_result, status,
                   create_time, update_time
            FROM error_feedback
            WHERE feedback_id = ?
        """
        results = db_query(sql, (feedback_id,))
        if not results:
            return None
            
        result = results[0]
        return {
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
    
    @staticmethod
    def delete_error_feedback(feedback_id: str) -> bool:
        """删除错误反馈记录"""
        try:
            db_execute("DELETE FROM error_feedback WHERE feedback_id = ?", (feedback_id,))
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_error_feedbacks_by_session(session_id: str) -> list:
        """根据会话ID获取错误反馈列表"""
        sql = """
            SELECT feedback_id, user_id, session_id, chat_messages, 
                   feedback_error_type, feedback_error_detail, auto_fix_result, status,
                   create_time, update_time
            FROM error_feedback
            WHERE session_id = ?
            ORDER BY create_time DESC
        """
        results = db_query(sql, (session_id,))
        feedbacks = []
        for result in results:
            feedbacks.append({
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
            })
        return feedbacks