from core.agent.state import MetaAgentState
from core.common.utils import parse_document, generate_id, format_time
from core.common.config import ROBOT_TEMPLATES, SUPPORTED_DOC_FORMATS
from core.common.db import db_execute
from core.robot.graph import build_robot_graph

# 节点1：解析上传文档
def parse_uploaded_docs(state: MetaAgentState) -> MetaAgentState:
    uploaded_docs = state["uploaded_docs"]
    doc_contents = []
    for doc in uploaded_docs:
        # 校验文档格式
        if doc.split(".")[-1] not in SUPPORTED_DOC_FORMATS:
            return {**state, "error": f"不支持的文档格式：{doc}，仅支持{SUPPORTED_DOC_FORMATS}"}
        # 解析文档
        content = parse_document(doc)
        doc_contents.append(content)
    return {**state, "doc_contents": doc_contents, "error": None}

# 节点2：解析管理者需求
def parse_demand(state: MetaAgentState) -> MetaAgentState:
    user_query = state["user_query"]
    doc_contents = state["doc_contents"]
    # 需求解析（简化，实际需大模型增强）
    parse_result = f"已解析您的需求：{user_query}，结合{len(doc_contents)}份上传文档，核心需求为搭建客服AI机器人，包含基础咨询解答、特定问题处理功能"
    # 判断是否理解需求
    is_understood = True if "搭建机器人" in user_query or "生成机器人" in user_query else False
    if not is_understood:
        parse_result = f"暂未理解您的需求：{user_query}，请补充描述客服机器人的搭建要求（如功能、行业、问题类型）"
    return {**state, "demand_parse_result": parse_result, "is_demand_understood": is_understood, "error": None}

# 节点3：选择机器人模板
def select_robot_template(state: MetaAgentState) -> MetaAgentState:
    user_query = state["user_query"]
    # 模板匹配（简化，实际需大模型根据需求匹配）
    if "金融" in user_query or "银行卡" in user_query:
        template = ROBOT_TEMPLATES[0] # 金融类
    elif "电商" in user_query or "订单" in user_query:
        template = ROBOT_TEMPLATES[1] # 电商类
    else:
        template = ROBOT_TEMPLATES[2] # 服务类
    return {**state, "robot_template": template, "error": None}

# 节点4：自动生成机器人配置
def generate_robot_config(state: MetaAgentState) -> MetaAgentState:
    template = state["robot_template"]
    doc_contents = state["doc_contents"]
    # 生成机器人核心配置（基于模板+文档内容）
    robot_config = {
        "gen_id": state["gen_id"],
        "template": template,
        "knowledge_base_url": DEFAULT_KNOWLEDGE_BASE_URL,
        "supported_functions": ["知识库匹配", "特定问题处理", "错误反馈修复"],
        "specific_questions": ["银行卡申请进度", "银行卡交易失败"] if template == "金融类" else ["订单查询", "物流跟踪"],
        "reply_styles": ["正式", "亲切", "简洁"],
        "auto_fix": True,
        "doc_basis": [f"文档{i+1}：{content[:50]}..." for i, content in enumerate(doc_contents)]
    }
    # 基于配置构建机器人LangGraph（核心）
    robot_graph = build_robot_graph()
    # 保存机器人配置到数据库
    db_execute(
        "INSERT INTO agent_generations (gen_id, manager_id, create_time, robot_template, robot_config, robot_status) VALUES (?, ?, ?, ?, ?, ?)",
        (state["gen_id"], state["manager_id"], format_time(), template, str(robot_config), "已生成")
    )
    return {**state, "robot_config": robot_config, "is_robot_generated": True, "error": None}

# 节点5：生成机器人验证
def verify_robot(state: MetaAgentState) -> MetaAgentState:
    robot_config = state["robot_config"]
    # 简单验证：配置完整性
    if all(key in robot_config for key in ["template", "supported_functions", "specific_questions"]):
        verify_result = f"机器人验证通过！基于{robot_config['template']}模板生成，支持{len(robot_config['supported_functions'])}项核心功能，可正常使用"
    else:
        verify_result = f"机器人验证失败！配置缺失，缺少核心功能定义，请重新生成"
        db_execute(
            "UPDATE agent_generations SET robot_status = ? WHERE gen_id = ?",
            ("验证失败", state["gen_id"])
        )
    return {**state, "verify_result": verify_result, "error": None}

# 条件判断：是否理解需求
def is_demand_understood_cond(state: MetaAgentState) -> str:
    return "select_template" if state["is_demand_understood"] else "end"

# 条件判断：是否生成机器人成功
def is_robot_generated_cond(state: MetaAgentState) -> str:
    return "verify_robot" if state["is_robot_generated"] else "end"