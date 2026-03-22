from langchain_core.messages import AIMessage, SystemMessage

from core.robot.state import CustomerServiceRobotState
from core.common.utils import crawl_knowledge_base, format_reply, generate_id, format_time
from core.common.config import ERROR_TYPES
from core.common.db import db_execute, db_query
from core.common.qwen_utils import generate_response_with_qwen, extract_serial_number_with_qwen, get_qwen_model
from core.common.vector_store import KnowledgeBaseVectorStore
from core.common.specific_question_service import SpecificQuestionService
from core.common.error_feedback_service import ErrorFeedbackService
from core.robot.tools import query_bank_card_apply_progress, query_bank_card_trans_fail
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import re,json

# 节点1：加载知识库内容
def load_knowledge_base(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    kb_url = state["knowledge_base_url"]
    kb_content = crawl_knowledge_base(kb_url)
    return {**state, "knowledge_base_content": kb_content}

# 节点2：问题类型判断（使用Qwen3大模型分析）
def judge_question_type(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    question = state["question"].strip()
    messages = state["messages"]
    
    # 无效问题判断（乱码、无意义字符、空内容）
    if not question or all(c in "~!@#$%^&*()_+{}|[]\;':\",./<>?" for c in question):
        return { "classification": "invalid"}
    
    if state['classification'] == "error_feedback":
        return {}
    
    try:
        # 获取启用的特殊问题流程
        enabled_specific_questions = SpecificQuestionService.get_enabled_specific_questions()
        specific_questions_str = SpecificQuestionService.format_specific_questions_for_prompt(enabled_specific_questions)
        
        # Use Qwen3 to analyze question type
        model = get_qwen_model()
        
        prompt = SystemMessage(content=
            f"""You are an expert customer service question classifier. Analyze the following customer question and classify it into one of these categories:
            
            Categories:
            - "invalid": The question is meaningless, contains only symbols, or is empty
            - "casual_chat": Greetings (like "hello", "hi"), emotional expressions (like "I'm frustrated", "thanks"), or casual conversation attempts with no specific service request
            - "general_kb": General questions that should be answered from the knowledge base
            {specific_questions_str}
            
            Respond with ONLY the category name (invalid, casual_chat, bank_card_apply, bank_card_trans_fail, general_kb, or the specific question key):"""
        )
        
        result = model.invoke([*messages,prompt])

        
        # Clean and parse the result
        classification = result.content.strip().lower()

        return { "classification": classification}
            
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
                return {"classification": "casual_chat", "is_invalid_question": False}
                
        for kw, type_ in specific_keywords.items():
            if kw in question:
                return {**state, "classification": type_, "is_invalid_question": False}
        # Default to general knowledge base question
        return { "classification": None, "is_invalid_question": False}

# 节点3：知识库匹配
def match_kb_node(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    question = state["messages"][-1].content
    
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
            return {"messages":[AIMessage(content="未找到有效的答案")]}
            
    except Exception as e:
        # 向量库查询失败或未找到匹配，生成未匹配错误反馈
        feedback_id = generate_id("feedback")
        chat_messages_str = str(state["messages"])
        
        # 保存错误反馈到数据库 - 使用新表结构
        db_execute(
            """INSERT INTO error_feedback 
               (feedback_id, user_id, session_id, chat_messages, feedback_error_type, 
                feedback_error_detail, auto_fix_result, status, create_time, update_time) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (feedback_id, state["user_id"], state["session_id"], chat_messages_str, 
             ERROR_TYPES[0], f"问题：{question} 未在知识库中匹配到答案", 
             None, "待修复", format_time(), format_time())
        )
        return {"messages":[AIMessage(content=f"未找到有效的答案")]}

# 节点4：特定问题工具调用
def handle_specific_question(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    classification = state["classification"]
    question = state["question"]
    user_id = state["user_id"]
    messages = state["messages"]
    
    try:
        # Use SpecificQuestionService to query the specific_question_flows table
        flow_config = SpecificQuestionService.get_specific_question_flow(classification)
        
        if flow_config:
            # Use dynamic flow configuration from database
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
            
            result = llm_with_tools.invoke([*messages,sm])

            # 增加act-think循环计数器
            current_cycle_count = state.get("act_think_cycle_count", 0)
            new_cycle_count = current_cycle_count + 1

            return {"messages":[result],"act_think_cycle_count": new_cycle_count}
            
        else:
            # No flow configuration found, fallback to generic response
            reply = f"Sorry, I cannot handle the specific question type '{classification}' at the moment."

            # 增加act-think循环计数器
            current_cycle_count = state.get("act_think_cycle_count", 0)
            new_cycle_count = current_cycle_count + 1

            return {"messages":[AIMessage(content=reply)],"act_think_cycle_count": new_cycle_count}
    except Exception as e:
        raise e

# 节点5：无效问题处理
def handle_invalid_question(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    reply = format_reply("你提出的问题无效，请提出具体的客服咨询问题，我将为你解答！", state["reply_style"])
    return {"messages": [AIMessage(content=reply)], "reply": reply}


# 节点6：系统故障兜底
def handle_system_error(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    reply = format_reply("抱歉，当前系统繁忙，请稍后再试，或联系人工客服（400-000-0000）！", state["reply_style"])
    return {"messages": [AIMessage(content=reply)], "reply": reply}

def call_specific_tool_cond(state: CustomerServiceRobotState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "call_tool"
    return "end"


# 节点7：错误自动修复
def auto_fix_error(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    """
    自动修复错误函数，根据用户的历史对话和错误反馈来尝试修复错误，
    同时把该错误信息记录到错误记录表中
    """
    # 获取当前会话的完整消息历史
    messages = state["messages"]
    if not messages:
        return {"messages": [AIMessage(content="No message history available, unable to perform error repair.")]}
    
    # 从最后一条消息中提取错误反馈信息（JSON格式）
    content = messages[-1].content
    
    
    error_feedback_data = json.loads(content)
    feedback_error_type = error_feedback_data.get("feedback_error_type")
    feedback_error_detail = error_feedback_data.get("feedback_error_detail")
        
            

    
    # 创建错误反馈记录
    feedback_id = ErrorFeedbackService.create_error_feedback(
        user_id=state["user_id"],
        session_id=state["session_id"],
        chat_messages=str(messages),
        feedback_error_type=feedback_error_type,
        feedback_error_detail=feedback_error_detail,
        status=ErrorFeedbackService.STATUS_PENDING
    )
    
    # 使用历史消息调用大模型尝试修复
    try:
        model = get_qwen_model()
        
        # 构建英文系统消息提示词，要求返回特定格式
        system_message = SystemMessage(content="""You are an intelligent customer service assistant tasked with automatically repairing errors based on the complete conversation history and error feedback information.

Your task is to carefully analyze the entire conversation history and the error feedback provided, then determine if you can provide an accurate and professional response.

You MUST respond in the following EXACT format:
result[true]:your_repair_answer_here
OR
result[false]:reason_why_cannot_repair

Where:
- Use "result[true]" if you can provide a reasonable answer based on the available information
- Use "result[false]" if the information is insufficient to provide an accurate answer or if human assistance is required
- Replace "your_repair_answer_here" with your actual repair answer when using result[true]
- Replace "reason_why_cannot_repair" with a brief explanation when using result[false]

Do not include any other text or formatting in your response. Only output the result in the specified format.""")
        
        
        auto_fix_result = model.invoke([*messages,system_message])
        
        # 解析大模型返回的特定格式结果
        auto_fix_content = auto_fix_result.content
        
        # 使用正则表达式解析结果格式
        match = re.search(r'result\[(true|false)\]:(.*)', auto_fix_content.strip(), re.IGNORECASE)
        is_repairable = False
        if match:
            is_repairable = match.group(1).lower() == 'true'
            fix_result = match.group(2).strip()
            
            if is_repairable:
                # 能够自动修复
                status = ErrorFeedbackService.STATUS_AUTO_FIXED
                fix_desc = "Successfully repaired automatically using large language model"
                auto_fix_result_content = fix_result
            else:
                # 无法自动修复，标记为转人工
                status = ErrorFeedbackService.STATUS_PENDING
                fix_desc = "Human customer service assistance required"
                auto_fix_result_content = f"Unable to automatically repair: {fix_result}"
        else:
            # 如果格式不符合预期，标记为无法修复
            status = ErrorFeedbackService.STATUS_PENDING
            fix_desc = "Automatic repair failed due to unexpected response format"
            auto_fix_result_content = f"Unexpected response format from model: {auto_fix_content[:200]}..."
            is_repairable = False
            
    except Exception as e:
        # 大模型调用失败，标记为转人工
        status = ErrorFeedbackService.STATUS_PENDING
        fix_desc = f"Automatic repair failed: {str(e)}"
        auto_fix_result_content = "Automatic repair failed, recommend transferring to human customer service"
        is_repairable = False
    
    # 更新错误反馈记录
    ErrorFeedbackService.update_error_feedback(
        feedback_id=feedback_id,
        auto_fix_result=auto_fix_result_content,
        status=status
    )

    return {"messages":[AIMessage(content=auto_fix_result_content)],"auto_fix_result":is_repairable,"feedback_id":feedback_id}

# 节点8：处理闲聊、打招呼和情绪表达
def handle_casual_chat(state: CustomerServiceRobotState) -> CustomerServiceRobotState:
    messages = state["messages"]
    
    # Use Qwen to generate an appropriate friendly response
    
    system_message = SystemMessage(f"""You are a friendly customer service assistant. Respond appropriately to greetings, emotional expressions, or casual chat, but gently guide the conversation back to customer service topics.""")
    
    model = get_qwen_model()
    result = model.invoke([*messages, system_message])
    
    return {"messages": [result]}

def reply(state: CustomerServiceRobotState)-> CustomerServiceRobotState:
    last = state["messages"][-1]

    return {"reply": last.content}


def question_dispatch_cond(state: CustomerServiceRobotState) -> str:

    classification = state["classification"]

    if classification in ["invalid","general_kb","casual_chat","error_feedback"]:
        return classification
    else:
        return "specific_question"
        
