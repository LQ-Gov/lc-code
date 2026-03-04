from core.robot.state import CustomerServiceRobotState
from core.robot.tools import TOOL_MAP, match_knowledge_base
from core.common.utils import crawl_knowledge_base, format_reply, generate_id, format_time
from core.common.config import ERROR_TYPES
from core.common.db import db_execute

# 节点1：加载知识库内容
def load_knowledge_base(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    kb_url = state["knowledge_base_url"]
    kb_content = crawl_knowledge_base(kb_url)
    return {**state, "knowledge_base_content": kb_content}

# 节点2：问题类型判断（无效问题/特定问题/普通知识库问题）
def judge_question_type(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    question = state["question"].strip()
    # 无效问题判断（乱码、无意义字符、空内容）
    if not question or all(c in "~!@#$%^&*()_+{}|[]\;':\",./<>?" for c in question):
        return {**state, "is_invalid_question": True}
    # 特定问题判断（银行卡申请进度、交易失败）
    specific_keywords = {
        "申请进度": "bank_card_apply",
        "交易失败": "bank_card_trans_fail",
        "流水号": "bank_card_trans_fail"
    }
    for kw, type_ in specific_keywords.items():
        if kw in question:
            return {**state, "specific_question_type": type_, "is_invalid_question": False}
    # 普通知识库问题
    return {**state, "specific_question_type": None, "is_invalid_question": False}

# 节点3：知识库匹配
def match_kb_node(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    question = state["question"]
    kb_content = state["knowledge_base_content"]
    # 调用知识库匹配工具
    match_result = match_knowledge_base.invoke({"question": question, "kb_content": kb_content})
    if not match_result["is_match"]:
        # 生成未匹配错误反馈
        feedback_id = generate_id("feedback")
        error_feedback = {
            "feedback_id": feedback_id,
            "error_type": ERROR_TYPES[0], # 知识库未匹配到正确答案
            "error_desc": f"问题：{question} 未在知识库中匹配到答案",
            "fix_status": "未修复"
        }
        # 保存错误反馈到数据库
        db_execute(
            "INSERT INTO error_feedback (feedback_id, session_id, question, robot_reply, error_type, error_desc, create_time, fix_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (feedback_id, state["session_id"], question, "", ERROR_TYPES[0], error_feedback["error_desc"], format_time(), "未修复")
        )
        return {**state, "error_feedback": error_feedback, "tool_call_result": None}
    # 匹配成功，生成回复
    reply = format_reply(match_result["answer"], state["reply_style"])
    return {**state, "reply": reply, "error_feedback": None, "tool_call_result": None}

# 节点4：特定问题工具调用
def call_specific_tool_node(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    specific_type = state["specific_question_type"]
    question = state["question"]
    user_id = state["user_id"]
    try:
        if specific_type == "bank_card_apply":
            # 调用银行卡申请进度工具
            tool_result = TOOL_MAP["query_bank_card_apply_progress"].invoke({"user_id": user_id})
            reply = format_reply(f"你的银行卡申请进度为：{tool_result['progress']}，{tool_result['tips']}", state["reply_style"])
        elif specific_type == "bank_card_trans_fail":
            # 提取流水号（若未提供，提示客户）
            if "serial_no" not in question and "流水号" in question:
                reply = format_reply("请提供该笔交易的流水号（可在APP订单详情/短信通知中查询），我将为你查询失败原因！", state["reply_style"])
                tool_result = None
            else:
                # 模拟提取流水号（实际需NLP解析，此处简化为固定值）
                serial_no = "TRX" + generate_id("")
                tool_result = TOOL_MAP["query_bank_card_trans_fail"].invoke({"serial_no": serial_no})
                reply = format_reply(f"交易失败原因：{tool_result['fail_reason']}，解决方案：{tool_result['solution']}", state["reply_style"])
        else:
            tool_result = None
            reply = format_reply("暂不支持该问题的查询，请尝试其他提问方式！", state["reply_style"])
        # 封装工具调用结果
        tool_call_result = {
            "tool_name": TOOL_MAP[specific_type].name if specific_type else None,
            "result": tool_result or {},
            "success": True,
            "error": None
        }
        return {**state, "reply": reply, "tool_call_result": tool_call_result, "error_feedback": None}
    except Exception as e:
        # 工具调用失败，生成错误反馈
        feedback_id = generate_id("feedback")
        error_feedback = {
            "feedback_id": feedback_id,
            "error_type": ERROR_TYPES[3], # 工具调用失败
            "error_desc": f"特定问题工具调用失败：{str(e)}",
            "fix_status": "未修复"
        }
        db_execute(
            "INSERT INTO error_feedback (feedback_id, session_id, question, robot_reply, error_type, error_desc, create_time, fix_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (feedback_id, state["session_id"], question, "", ERROR_TYPES[3], error_feedback["error_desc"], format_time(), "未修复")
        )
        return {**state, "error_feedback": error_feedback, "tool_call_result": None, "is_system_error": True}

# 节点5：无效问题处理
def handle_invalid_question(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    reply = format_reply("你提出的问题无效，请提出具体的客服咨询问题，我将为你解答！", state["reply_style"])
    return {**state, "reply": reply, "error_feedback": None}

# 节点6：系统故障兜底
def handle_system_error(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    reply = format_reply("抱歉，当前系统繁忙，请稍后再试，或联系人工客服（400-000-0000）！", state["reply_style"])
    return {**state, "reply": reply}

# 节点7：错误自动修复
def auto_fix_error(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    error_feedback = state["error_feedback"]
    if not error_feedback or error_feedback["fix_status"] == "已修复":
        return state
    # 不同错误类型的修复逻辑
    error_type = error_feedback["error_type"]
    fix_desc = ""
    if error_type == ERROR_TYPES[0]: # 知识库未匹配
        # 修复：补充问题到知识库（简化，实际需管理者确认）
        fix_desc = f"已将问题「{state['question']}」补充至知识库，后续可匹配"
    elif error_type == ERROR_TYPES[1]: # 操作步骤错误
        # 修复：修正特定问题处理步骤
        fix_desc = "已修正特定问题的操作步骤，重新调用工具可正常查询"
    elif error_type == ERROR_TYPES[3]: # 工具调用失败
        # 修复：重启工具调用服务
        fix_desc = "已重启工具调用服务，可重新发起查询"
    # 更新错误反馈状态
    db_execute(
        "UPDATE error_feedback SET fix_status = ?, fix_time = ? WHERE feedback_id = ?",
        ("已修复", format_time(), error_feedback["feedback_id"])
    )
    # 更新状态
    error_feedback["fix_status"] = "已修复"
    return {**state, "error_feedback": error_feedback, "fix_desc": fix_desc}

# 条件判断：是否为无效问题
def is_invalid_question_cond(state: CustomerServiceRobotState) -> str:
    return "handle_invalid" if state["is_invalid_question"] else "judge_specific"

# 条件判断：是否为特定问题
def is_specific_question_cond(state: CustomerServiceRobotState) -> str:
    return "call_specific_tool" if state.get("specific_question_type") else "match_kb"

# 条件判断：是否系统故障/有错误
def has_error_cond(state: CustomerServiceRobotState) -> str:
    if state["is_system_error"]:
        return "handle_system_error"
    elif state["error_feedback"]:
        return "auto_fix_error"
    else:
        return "end"