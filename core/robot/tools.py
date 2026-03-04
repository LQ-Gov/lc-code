from langchain_core.tools import tool
from core.common.utils import generate_id
import random

# 模拟：银行卡申请进度查询工具
@tool
def query_bank_card_apply_progress(user_id: str) -> dict:
    """
    用于查询客户的银行卡申请进度，入参为客户ID
    :param user_id: 客户唯一ID
    :return: 包含进度和关键节点的字典
    """
    # 模拟进度：审核中、已通过、已邮寄、已签收、审核驳回
    progress_list = ["审核中", "已通过", "已邮寄", "已签收", "审核驳回"]
    progress = random.choice(progress_list)
    return {
        "apply_id": generate_id("apply"),
        "user_id": user_id,
        "progress": progress,
        "update_time": "2025-10-20 15:30:00",
        "tips": "审核驳回可在APP提交重新审核申请" if progress == "审核驳回" else ""
    }

# 模拟：银行卡交易失败查询工具
@tool
def query_bank_card_trans_fail(serial_no: str) -> dict:
    """
    用于根据流水号查询银行卡交易失败原因，入参为交易流水号
    :param serial_no: 交易流水号（APP订单详情/短信可查）
    :return: 包含失败原因和解决方案的字典
    """
    # 模拟失败原因：余额不足、系统故障、卡片异常、商户端问题
    fail_reason_list = ["余额不足", "系统故障", "卡片异常", "商户端问题"]
    fail_reason = random.choice(fail_reason_list)
    solution_map = {
        "余额不足": "请先为银行卡充值足够余额后重新发起交易",
        "系统故障": "当前支付系统临时故障，请稍后再试",
        "卡片异常": "请联系银行核对卡片状态（是否冻结/挂失）",
        "商户端问题": "请联系商户确认收款账户是否正常"
    }
    return {
        "serial_no": serial_no,
        "fail_reason": fail_reason,
        "solution": solution_map[fail_reason],
        "contact_way": "客服热线：400-000-0000"
    }

# 知识库匹配工具
@tool
def match_knowledge_base(question: str, kb_content: str) -> dict:
    """
    用于从知识库内容中匹配客户问题的答案，入参为客户问题和知识库内容
    :param question: 客户问题
    :param kb_content: 知识库文本内容
    :return: 包含是否匹配和答案的字典
    """
    # 简易匹配：关键词匹配（可替换为向量匹配提升精度）
    keywords = question.strip().split()
    match_lines = []
    for line in kb_content.split("\n"):
        if any(key in line for key in keywords) and line.strip():
            match_lines.append(line.strip())
    if match_lines:
        return {"is_match": True, "answer": "\n".join(match_lines[:3])} # 取前3条匹配结果
    else:
        return {"is_match": False, "answer": ""}

# 工具列表
ROBOT_TOOLS = [
    query_bank_card_apply_progress,
    query_bank_card_trans_fail,
    match_knowledge_base
]

# 工具映射
TOOL_MAP = {tool.name: tool for tool in ROBOT_TOOLS}