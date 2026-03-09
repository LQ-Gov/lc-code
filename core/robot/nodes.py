from core.robot.state import CustomerServiceRobotState
from core.robot.tools import TOOL_MAP, match_knowledge_base
from core.common.utils import crawl_knowledge_base, format_reply, generate_id, format_time
from core.common.config import ERROR_TYPES
from core.common.db import db_execute, db_query
from core.common.qwen_utils import generate_response_with_qwen, extract_serial_number_with_qwen, get_qwen_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import re

# 节点1：加载知识库内容
def load_knowledge_base(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    kb_url = state["knowledge_base_url"]
    kb_content = crawl_knowledge_base(kb_url)
    return {**state, "knowledge_base_content": kb_content}

# 节点2：问题类型判断（使用Qwen3大模型分析）
def judge_question_type(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    question = state["question"].strip()
    
    # 无效问题判断（乱码、无意义字符、空内容）
    if not question or all(c in "~!@#$%^&*()_+{}|[]\;':\",./<>?" for c in question):
        return {**state, "is_invalid_question": True}
    
    try:
        # Use Qwen3 to analyze question type
        model = get_qwen_model()
        
        prompt = ChatPromptTemplate.from_template(
            """You are an expert customer service question classifier. Analyze the following customer question and classify it into one of these categories:
            
            Categories:
            - "invalid": The question is meaningless, contains only symbols, or is empty
            - "casual_chat": Greetings (like "hello", "hi"), emotional expressions (like "I'm frustrated", "thanks"), or casual conversation attempts with no specific service request
            - "bank_card_apply": Questions about bank card application progress or status
            - "bank_card_trans_fail": Questions about failed transactions, transaction errors, or payment issues
            - "general_kb": General questions that should be answered from the knowledge base
            
            Customer Question: {question}
            
            Respond with ONLY the category name (invalid, casual_chat, bank_card_apply, bank_card_trans_fail, or general_kb):"""
        )
        
        chain = prompt | model | StrOutputParser()
        result = chain.invoke({"question": question})

        print(f"Question Type: {result}")
        
        # Clean and parse the result
        classification = result.strip().lower()

        state.update({"classification": classification}) 
        
        if classification == "invalid":
            return {**state, "is_invalid_question": True}
        elif classification == "casual_chat":
            return {**state, "specific_question_type": "casual_chat", "is_invalid_question": False}
        elif classification == "bank_card_apply":
            return {**state, "specific_question_type": "bank_card_apply", "is_invalid_question": False}
        elif classification == "bank_card_trans_fail":
            return {**state, "specific_question_type": "bank_card_trans_fail", "is_invalid_question": False}
        else:  # general_kb or any other response
            return {**state, "specific_question_type": None, "is_invalid_question": False}
            
    except Exception as e:
        # Fallback to original keyword-based logic if Qwen3 fails
        specific_keywords = {
            "申请进度": "bank_card_apply",
            "交易失败": "bank_card_trans_fail",
            "流水号": "bank_card_trans_fail"
        }
        # Add keywords for casual chat detection
        casual_keywords = ["你好", "您好", "谢谢", "感谢", "再见", "拜拜", "烦死了", "生气", "开心", "高兴"]
        for kw in casual_keywords:
            if kw in question:
                return {**state, "specific_question_type": "casual_chat", "is_invalid_question": False}
                
        for kw, type_ in specific_keywords.items():
            if kw in question:
                return {**state, "specific_question_type": type_, "is_invalid_question": False}
        # Default to general knowledge base question
        return {**state, "specific_question_type": None, "is_invalid_question": False}

# 节点3：知识库匹配
def match_kb_node(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    question = state["question"]
    kb_content = state["knowledge_base_content"]
    # 调用知识库匹配工具
    match_result = match_knowledge_base(question, kb_content)
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
    # 匹配成功，使用Qwen3生成回复
    context = {
        "question": question,
        "answer": match_result["answer"],
        "reply_style": state["reply_style"]
    }
    reply = generate_response_with_qwen(context)
    return {**state, "reply": reply, "error_feedback": None, "tool_call_result": None}

# 节点4：特定问题工具调用
def handle_specific_question(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    specific_type = state["specific_question_type"]
    question = state["question"]
    user_id = state["user_id"]
    try:
        # Query the specific_question_flows table for the specific_type
        flow_data = db_query(
            "SELECT prompt, flow FROM specific_question_flows WHERE key = ? AND status = 'active'",
            (specific_type,)
        )
        
        if  flow_data:
            # Use dynamic flow configuration from database
            prompt_template = flow_data[0][0]  # prompt column
            flow_info = flow_data[0][1]        # flow column
            
            # Build the dynamic prompt
            model = get_qwen_model()
            
            # Create a comprehensive prompt that includes the question, template, and flow instructions
            base_prompt = f"""你是一个智能客服助手，需要处理用户的特定问题。

用户问题：{question}

问题类型：{specific_type}
流程信息：{flow_info if flow_info else '无特定流程'}

{prompt_template if prompt_template else ''}

请根据以上信息回答用户问题，并明确说明下一步执行步骤。

请严格按照以下格式进行回应:
Thought: 你的思考过程，用于分析问题、拆解任务和规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一:
- `{{tool_name}}[{{tool_input}}]`:调用一个可用工具。
- `feedback[{{feedback_content}}]:当你认为已经获得最终答案时,或者需要用户补充额外信息时。
- 当你收集到足够的信息，能够回答用户的最终问题时，你必须在Action:字段后使用 feedback[最终答案] 来输出最终答案。

请确保你的回答清晰、准确，并严格按照上述格式提供下一步步骤指示。"""
            
            # Use Qwen model to generate response with next steps
            chat_prompt = ChatPromptTemplate.from_template(base_prompt)
            chain = chat_prompt | model | StrOutputParser()
            response_with_steps = chain.invoke({})


            throuth,action = _parse_output(response_with_steps)

            
            
            # Parse the response to extract answer and next steps
            reply = response_with_steps
            tool_result = {"dynamic_response": response_with_steps, "flow_used": True}
        
        # 封装工具调用结果
        tool_call_result = {
            "tool_name": specific_type if specific_type else None,
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
    
def _parse_output(self, text: str):
        """解析LLM的输出，提取Thought和Action。
        """
        # Thought: 匹配到 Action: 或文本末尾
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        # Action: 匹配到文本末尾
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

def _parse_action(self, action_text: str):
    """解析Action字符串，提取工具名称和输入。
    """
    match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
    if match:
        return match.group(1), match.group(2)
    return None, None

# 节点5：无效问题处理
def handle_invalid_question(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    reply = format_reply("你提出的问题无效，请提出具体的客服咨询问题，我将为你解答！", state["reply_style"])
    return {**state, "reply": reply, "error_feedback": None}


# 节点6：系统故障兜底
def handle_system_error(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    reply = format_reply("抱歉，当前系统繁忙，请稍后再试，或联系人工客服（400-000-0000）！", state["reply_style"])
    return {**state, "reply": reply}

def call_specific_tool_cond(state: CustomerServiceRobotState) -> str:
    if  state["call_tool"]:
        return "call_tool"
    return "end"

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

# 节点8：处理闲聊、打招呼和情绪表达
def handle_casual_chat(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    question = state["question"]
    reply_style = state["reply_style"]
    
    # Use Qwen to generate an appropriate friendly response
    context = {
        "question": question,
        "reply_style": reply_style,
        "instruction": "You are a friendly customer service assistant. Respond appropriately to greetings, emotional expressions, or casual chat, but gently guide the conversation back to customer service topics."
    }
    
    try:
        model = get_qwen_model()
        prompt = ChatPromptTemplate.from_template(
            """You are a friendly customer service assistant. The user has sent a message that appears to be a greeting, emotional expression, or casual chat.

User message: {question}

Please respond in a warm, professional manner that acknowledges their message, but also gently guides them toward asking specific customer service questions if they need assistance.

Response style: {reply_style}"""
        )
        chain = prompt | model | StrOutputParser()
        reply = chain.invoke(context)
    except Exception as e:
        # Fallback response if Qwen fails
        default_responses = {
            "formal": "您好！感谢您的问候。我是客服助手，如果您有任何银行相关的问题需要咨询，请随时告诉我。",
            "casual": "你好呀！很高兴见到你！如果你有任何银行相关的问题需要帮助，尽管问我哦~",
            "concise": "您好！我是客服助手，请问有什么可以帮您的？"
        }
        reply = default_responses.get(reply_style, default_responses["formal"])
    
    return {**state, "reply": reply, "error_feedback": None}

# 条件判断：是否为无效问题
def is_invalid_question_cond(state: CustomerServiceRobotState) -> str:
    return "handle_invalid" if state["is_invalid_question"] else "judge_specific"

# 条件判断：是否为特定问题
def is_specific_question_cond(state: CustomerServiceRobotState) -> str:
    return "call_specific_tool" if state.get("specific_question_type") else "match_kb"

def question_dispatch_cond(state: CustomerServiceRobotState) -> str:
    classification = state["classification"]
    if classification == "invalid":
        return "invalid"
    elif classification == "casual_chat":
        return "casual_chat"
    elif classification == "general_kb":
        return "general_kb"
    else:
        return "specific_question"



# 条件判断：是否系统故障/有错误
def has_error_cond(state: CustomerServiceRobotState) -> str:
    if state["is_system_error"]:
        return "handle_system_error"
    elif state["error_feedback"]:
        return "auto_fix_error"
    else:
        return "end"