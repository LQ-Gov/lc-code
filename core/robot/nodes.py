from langchain_core.messages import AIMessage,SystemMessage

from core.robot.state import CustomerServiceRobotState
from core.common.utils import crawl_knowledge_base, format_reply, generate_id, format_time
from core.common.config import ERROR_TYPES
from core.common.db import db_execute, db_query
from core.common.qwen_utils import generate_response_with_qwen, extract_serial_number_with_qwen, get_qwen_model
from core.common.vector_store import KnowledgeBaseVectorStore
from core.common.specific_question_service import SpecificQuestionService
from core.robot.tools import query_bank_card_apply_progress, query_bank_card_trans_fail
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
    messages = state["messages"]
    history = "\n".join([f"{m.type}: {m.content}" for m in messages])
    
    # 无效问题判断（乱码、无意义字符、空内容）
    if not question or all(c in "~!@#$%^&*()_+{}|[]\;':\",./<>?" for c in question):
        return {**state, "is_invalid_question": True}
    
    try:
        # 获取启用的特殊问题流程
        enabled_specific_questions = SpecificQuestionService.get_enabled_specific_questions()
        specific_questions_str = SpecificQuestionService.format_specific_questions_for_prompt(enabled_specific_questions)
        
        # Use Qwen3 to analyze question type
        model = get_qwen_model()
        
        prompt = ChatPromptTemplate.from_template(
            """You are an expert customer service question classifier. Analyze the following customer question and classify it into one of these categories:
            
            Categories:
            - "invalid": The question is meaningless, contains only symbols, or is empty
            - "casual_chat": Greetings (like "hello", "hi"), emotional expressions (like "I'm frustrated", "thanks"), or casual conversation attempts with no specific service request
            - "general_kb": General questions that should be answered from the knowledge base
            {specific_questions}
            
            Customer Question: {question}
            history chat:{history}
            
            Respond with ONLY the category name (invalid, casual_chat, bank_card_apply, bank_card_trans_fail, general_kb, or the specific question key):"""
        )
        
        chain = prompt | model | StrOutputParser()
        result = chain.invoke({"question": question, "specific_questions": specific_questions_str,"history": history})

        
        # Clean and parse the result
        classification = result.strip().lower()

        state.update({"classification": classification}) 
        
        # 检查分类结果是否是启用的特殊问题key之一
        enabled_keys = [item["key"].lower() for item in enabled_specific_questions]
        if classification in enabled_keys:
            return { "specific_question_type": classification, "is_invalid_question": False}
        elif classification == "invalid":
            return { "is_invalid_question": True}
        elif classification == "casual_chat":
            return { "specific_question_type": "casual_chat", "is_invalid_question": False}
        else:  # general_kb or any other response
            return { "specific_question_type": None, "is_invalid_question": False}
            
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
                return {"specific_question_type": "casual_chat", "is_invalid_question": False}
                
        for kw, type_ in specific_keywords.items():
            if kw in question:
                return {**state, "specific_question_type": type_, "is_invalid_question": False}
        # Default to general knowledge base question
        return { "specific_question_type": None, "is_invalid_question": False}

# 节点3：知识库匹配
def match_kb_node(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    question = state["question"]
    
    # 使用向量库进行相似性搜索
    try:
        vector_store = KnowledgeBaseVectorStore()
        similar_results = vector_store.search_similar_questions(question, n_results=3)
        
        if similar_results and len(similar_results) > 0:
            # 获取最相似的结果（距离最小的）
            best_match = similar_results[0]
            answer = best_match["answer"]
            
            # 直接返回答案，不再调用大模型
            return {"messages":[AIMessage(content=answer)]}
        else:
            # 没有找到匹配结果
            raise Exception("No similar questions found in vector store")
            
    except Exception as e:
        # 向量库查询失败或未找到匹配，生成未匹配错误反馈
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
        return {"messages":[AIMessage(content=f"未找到有效的答案")]}

# 节点4：特定问题工具调用
def handle_specific_question(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    specific_type = state["specific_question_type"]
    question = state["question"]
    user_id = state["user_id"]
    messages = state["messages"]
    history = "\n".join([f"{m.type}: {m.content}" for m in messages])
    try:
        # Use SpecificQuestionService to query the specific_question_flows table
        flow_config = SpecificQuestionService.get_specific_question_flow(specific_type)
        
        if flow_config:
            # Use dynamic flow configuration from database
            prompt_template = flow_config["prompt"]
            flow_info = flow_config["flow"]
            
            # Build the dynamic prompt
            model = get_qwen_model()
            llm_with_tools = model.bind_tools([query_bank_card_apply_progress, query_bank_card_trans_fail])
            
            # Create a comprehensive prompt in English that includes the question, template, and flow instructions
            sm = SystemMessage(f"""You are an intelligent customer service assistant who needs to handle the user's specific question.

Flow Information: {flow_info if flow_info else 'No specific flow'}

Please answer the user's question based on the above information and clearly indicate the next execution steps.

Ensure your response is clear, accurate, and strictly follows the above format to provide next step instructions."""
            )
            
#             Please strictly follow the following response format:
# Thought: Your thinking process for analyzing the question, breaking down tasks, and planning next actions.
# Action: The action you decide to take, which must be one of the following formats:
# - `{{tool_name}}[{{tool_input}}]`: Call an available tool.
# - `feedback[{{feedback_content}}]`: When you have obtained the final answer or need the user to provide additional information.
# - When you have collected enough information to answer the user's final question, you must use feedback[final_answer] after the Action: field to output the final answer.
            
            # Use Qwen model to generate response with next steps
            # chat_prompt = ChatPromptTemplate.from_template(base_prompt)
            # chain = chat_prompt | llm_with_tools
            result = llm_with_tools.invoke([*messages,sm])

            print(result)

            return {"messages":[result]}
            
        else:
            # No flow configuration found, fallback to generic response
            reply = f"Sorry, I cannot handle the specific question type '{specific_type}' at the moment."
            tool_result = {
                "dynamic_response": None,
                "flow_used": False,
                "thought": None,
                "action": None,
                "next_step": "end_conversation"
            }
        
        # 封装工具调用结果，包含下一步要做的事情
        tool_call_result = {
            "tool_name": specific_type if specific_type else None,
            "result": tool_result,
            "success": True,
            "error": None,
            "next_step": tool_result.get("next_step", "end_conversation")
        }
        return {**state, "reply": reply, "tool_call_result": tool_call_result, "error_feedback": None}
    except Exception as e:
        # 工具调用失败，生成错误反馈
        # feedback_id = generate_id("feedback")
        # error_feedback = {
        #     "feedback_id": feedback_id,
        #     "error_type": ERROR_TYPES[3], # 工具调用失败
        #     "error_desc": f"特定问题工具调用失败：{str(e)}",
        #     "fix_status": "未修复"
        # }
        # db_execute(
        #     "INSERT INTO error_feedback (feedback_id, session_id, question, robot_reply, error_type, error_desc, create_time, fix_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        #     (feedback_id, state["session_id"], question, "", ERROR_TYPES[3], error_feedback["error_desc"], format_time(), "未修复")
        # )
        # return {**state, "error_feedback": error_feedback, "tool_call_result": None, "is_system_error": True}
        raise e

def _parse_output(text: str):
    """Parse LLM output to extract Thought and Action."""
    # Match Thought: until Action: or end of text
    thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
    # Match Action: until end of text
    action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
    
    thought = thought_match.group(1).strip() if thought_match else ""
    action = action_match.group(1).strip() if action_match else ""
    
    return thought, action

# 节点5：无效问题处理
def handle_invalid_question(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    reply = format_reply("你提出的问题无效，请提出具体的客服咨询问题，我将为你解答！", state["reply_style"])
    return {"messages": [AIMessage(content=reply)]}


# 节点6：系统故障兜底
def handle_system_error(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    reply = format_reply("抱歉，当前系统繁忙，请稍后再试，或联系人工客服（400-000-0000）！", state["reply_style"])
    return {"messages": [AIMessage(content=reply)]}

def call_specific_tool_cond(state: CustomerServiceRobotState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
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
        chain = prompt | model
        result = chain.invoke(context)
        return {"messages":[result]}
    except Exception as e:
        # Fallback response if Qwen fails
        default_responses = {
            "formal": "您好！感谢您的问候。我是客服助手，如果您有任何银行相关的问题需要咨询，请随时告诉我。",
            "casual": "你好呀！很高兴见到你！如果你有任何银行相关的问题需要帮助，尽管问我哦~",
            "concise": "您好！我是客服助手，请问有什么可以帮您的？"
        }
        reply = default_responses.get(reply_style, default_responses["formal"])
    
    return {"messages":[AIMessage(content=reply)]}

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
    
def replay(state: CustomerServiceRobotState)->CustomerServiceRobotState:
    last = state['messages'][-1]
    return {"reply": last.content}