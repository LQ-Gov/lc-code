from fastapi import FastAPI, Query, Body
from pydantic import BaseModel
from core.robot.graph import robot_invoke
from core.agent.graph import meta_agent_invoke
from core.common.utils import generate_id

app = FastAPI(title="客服AI机器人+元智能体API", version="1.0")

# 模型定义
class RobotConsultRequest(BaseModel):
    user_id: str
    question: str
    session_id: str = None
    kb_url: str = None
    reply_style: str = None

class MetaAgentGenerateRequest(BaseModel):
    manager_id: str
    user_query: str
    uploaded_docs: list = None

# 客服机器人咨询接口
@app.post("/api/robot/consult", summary="客户咨询客服机器人")
def robot_consult(req: RobotConsultRequest):
    result = robot_invoke(
        user_id=req.user_id,
        question=req.question,
        session_id=req.session_id,
        kb_url=req.kb_url,
        reply_style=req.reply_style
    )
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "session_id": result["session_id"],
            "reply": result["reply"],
            "error_feedback": result["error_feedback"],
            "tool_call_result": result["tool_call_result"]
        }
    }

# 元智能体生成机器人接口
@app.post("/api/meta-agent/generate", summary="管理者通过元智能体生成客服机器人")
def meta_agent_generate(req: MetaAgentGenerateRequest):
    result = meta_agent_invoke(
        manager_id=req.manager_id,
        user_query=req.user_query,
        uploaded_docs=req.uploaded_docs
    )
    return {
        "code": 200 if not result["error"] else 500,
        "msg": "success" if not result["error"] else result["error"],
        "data": {
            "gen_id": result["gen_id"],
            "demand_parse_result": result["demand_parse_result"],
            "robot_template": result["robot_template"],
            "robot_config": result["robot_config"],
            "verify_result": result["verify_result"]
        }
    }

# 健康检查接口
@app.get("/api/health", summary="服务健康检查")
def health_check():
    return {"code": 200, "msg": "service is running"}