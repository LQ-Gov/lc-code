import os
from typing import Dict, Any, List
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# Initialize Qwen3 model using OpenAI-compatible API
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_MODEL_NAME = os.getenv("QWEN_MODEL_NAME", "qwen-max")

def get_qwen_model():
    """Get Qwen3 model instance using OpenAI-compatible API"""
    if not QWEN_API_KEY:
        raise ValueError("QWEN_API_KEY environment variable is required")
    
    return ChatOpenAI(
        model_name=QWEN_MODEL_NAME,
        api_key=QWEN_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=0.3,
        max_tokens=2000
    )

def match_knowledge_base_with_qwen(question: str, kb_content: str) -> Dict[str, Any]:
    """Use Qwen3 to match question with knowledge base content"""
    try:
        model = get_qwen_model()
        
        # Create prompt for knowledge base matching
        prompt = ChatPromptTemplate.from_template(
            """You are a customer service assistant. Based on the following knowledge base content, 
            determine if you can answer the customer's question accurately.
            
            Knowledge Base Content:
            {kb_content}
            
            Customer Question:
            {question}
            
            If you can find a clear and accurate answer in the knowledge base, respond with:
            {{'is_match': true, 'answer': 'your_answer_here'}}
            
            If you cannot find a relevant answer, respond with:
            {{'is_match': false, 'answer': ''}}
            
            Only respond with the JSON format above, nothing else."""
        )
        
        chain = prompt | model | StrOutputParser()
        result_str = chain.invoke({"kb_content": kb_content, "question": question})
        
        # Parse the result (simplified - in production, use proper JSON parsing)
        if "'is_match': true" in result_str or '"is_match": true' in result_str:
            # Extract answer from result
            start_idx = result_str.find("'answer': '") if "'answer': '" in result_str else result_str.find('"answer": "')
            if start_idx != -1:
                start_idx += len("'answer': '") if "'answer': '" in result_str else len('"answer": "')
                end_idx = result_str.find("'", start_idx) if "'answer': '" in result_str else result_str.find('"', start_idx)
                answer = result_str[start_idx:end_idx] if end_idx != -1 else ""
            else:
                answer = ""
            return {"is_match": True, "answer": answer}
        else:
            return {"is_match": False, "answer": ""}
            
    except Exception as e:
        return {"is_match": False, "answer": "", "error": str(e)}

def generate_response_with_qwen(context: Dict[str, Any]) -> str:
    """Generate customer service response using Qwen3"""
    try:
        model = get_qwen_model()
        
        # Determine context type and create appropriate prompt
        if context.get("specific_question_type") == "bank_card_apply":
            prompt_template = """You are a helpful customer service representative for Atome Card.
            The customer asked about their bank card application progress.
            Progress status: {progress}
            Additional tips: {tips}
            
            Please provide a clear, friendly, and professional response to the customer."""
            
            prompt = ChatPromptTemplate.from_template(prompt_template)
            chain = prompt | model | StrOutputParser()
            return chain.invoke({
                "progress": context.get("progress", "Unknown"),
                "tips": context.get("tips", "")
            })
            
        elif context.get("specific_question_type") == "bank_card_trans_fail":
            prompt_template = """You are a helpful customer service representative for Atome Card.
            The customer asked about a failed transaction.
            Failure reason: {fail_reason}
            Solution: {solution}
            
            Please provide a clear, empathetic, and helpful response to the customer, 
            explaining the issue and the solution."""
            
            prompt = ChatPromptTemplate.from_template(prompt_template)
            chain = prompt | model | StrOutputParser()
            return chain.invoke({
                "fail_reason": context.get("fail_reason", "Unknown"),
                "solution": context.get("solution", "")
            })
            
        else:
            # General knowledge base response
            prompt_template = """You are a professional customer service representative.
            Answer the customer's question based on the provided information.
            
            Question: {question}
            Answer: {answer}
            
            Please format your response professionally and clearly."""
            
            prompt = ChatPromptTemplate.from_template(prompt_template)
            chain = prompt | model | StrOutputParser()
            return chain.invoke({
                "question": context.get("question", ""),
                "answer": context.get("answer", "")
            })
            
    except Exception as e:
        return f"Sorry, I encountered an error while processing your request: {str(e)}"

def extract_serial_number_with_qwen(question: str) -> str:
    """Use Qwen3 to extract serial number from customer question"""
    try:
        model = get_qwen_model()
        
        prompt = ChatPromptTemplate.from_template(
            """Extract the transaction serial number from the following customer message.
            If no serial number is found, respond with 'NOT_FOUND'.
            
            Customer message: {question}
            
            Serial number:"""
        )
        
        chain = prompt | model | StrOutputParser()
        result = chain.invoke({"question": question})
        
        return result.strip() if result.strip() != "NOT_FOUND" else ""
        
    except Exception:
        return ""