from typing import Dict, Any
from core.common.qwen_utils import match_knowledge_base_with_qwen, extract_serial_number_with_qwen
from langchain_core.tools import tool
@tool(description="Query bank card application progress")
def query_bank_card_apply_progress(user_id: str) -> Dict[str, Any]:
    """Simulate querying bank card application progress"""
    # In a real system, this would call an external API or database
    # For simulation purposes, return mock data based on user_id
    import random
    
    progress_options = [
        {"progress": "审核中", "tips": "请耐心等待，通常需要1-3个工作日"},
        {"progress": "已通过", "tips": "恭喜！您的银行卡已通过审核，正在制作中"},
        {"progress": "已邮寄", "tips": "您的银行卡已邮寄，请注意查收快递"},
        {"progress": "需要补充材料", "tips": "请登录APP上传身份证正反面照片"}
    ]
    
    return random.choice(progress_options)

@tool(description="Query bank card transaction failure reason")
def query_bank_card_trans_fail(serial_no: str) -> Dict[str, Any]:
    """Simulate querying bank card transaction failure reason"""
    # In a real system, this would call a transaction service API
    # For simulation purposes, return mock data based on serial_no
    import random
    
    failure_scenarios = [
        {
            "fail_reason": "余额不足",
            "solution": "请充值账户余额后重试交易"
        },
        {
            "fail_reason": "系统故障",
            "solution": "系统正在维护中，请稍后再试或联系客服"
        },
        {
            "fail_reason": "卡片异常",
            "solution": "请检查卡片状态或联系银行核对卡片信息"
        },
        {
            "fail_reason": "交易超时",
            "solution": "网络连接超时，请重新发起交易"
        }
    ]
    
    return random.choice(failure_scenarios)