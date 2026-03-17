from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi import UploadFile, File, Form
import os
from pydantic import BaseModel
from typing import List, Optional, Any
from core.robot.graph import robot_invoke
from core.agent.graph import dev_agent_invoke
from core.crawl.graph import crawler_graph
from core.crawl.state import CrawlState
from core.common.db import init_db
from datetime import datetime
import uuid

# 导入独立的API模块
from web.knowledge_base_api import kb_router
from web.special_flow_api import sf_router
from web.error_feedback_api import ef_router
from web.vector_store_api import vs_router
from web.config_api import config_router

app = FastAPI(title="客服AI机器人+元智能体API", version="1.0")

# Add CORS middleware to allow requests from UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册独立的API路由
app.include_router(kb_router)
app.include_router(sf_router)
app.include_router(ef_router)
app.include_router(vs_router)
app.include_router(config_router)

# 模型定义
class RobotConsultRequest(BaseModel):
    user_id: str
    question: str
    session_id: Optional[str] = None
    classification: Optional[str] = None
    reply_style: Optional[str] = None

class DevAgentRequest(BaseModel):
    user_id: str
    question: str
    session_id: Optional[str] = None
    history: Optional[List[Any]] = None
    action: Optional[str] = None
    filename: Optional[str] = None

class MetaAgentGenerateRequest(BaseModel):
    manager_id: str
    user_query: str
    uploaded_docs: Optional[list] = None

# 爬虫接口模型
class CrawlRequest(BaseModel):
    seed_url: str

# 文件上传目录
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 客服机器人咨询接口
@app.post("/api/robot/consult", summary="客户咨询客服机器人")
def robot_consult(req: RobotConsultRequest):
    result = robot_invoke(
        user_id=req.user_id,
        question=req.question,
        session_id=req.session_id,
        classification=req.classification,
        reply_style=req.reply_style
    )
    
    # 构建错误反馈信息
    error_feedback_info = None
    if result.get("feedback_id") or result.get("auto_fix_result") is not None:
        error_feedback_info = {
            "feedback_id": result.get("feedback_id"),
            "auto_fix_result": result.get("auto_fix_result")
        }
    
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "session_id": result["session_id"],
            "reply": result["reply"],
            "error_feedback_result": error_feedback_info,
            "tool_call_result": result["tool_call_result"]
        }
    }

# 开发代理接口
@app.post("/api/dev-agent/consult", summary="开发代理咨询接口")
def dev_agent_consult(req: DevAgentRequest):
    # 处理文件上传action
    if req.action == "upload_file" and req.filename:
        uploaded_files = [req.filename]
    else:
        uploaded_files = []
    
    result = dev_agent_invoke(
        user_id=req.user_id,
        question=req.question,
        session_id=req.session_id,
        history=req.history,
        uploaded_files=uploaded_files
    )
    
    return {
        "code": 200 if not result.get("error") else 500,
        "msg": "success" if not result.get("error") else result.get("error", "未知错误"),
        "data": {
            "session_id": result["session_id"],
            "reply": result["reply"],
            "tool_call_result": result["tool_call_result"],
            "thought_process": result["thought_process"],
            "is_final_answer": result["is_final_answer"]
        }
    }

# 文件上传接口
@app.post("/api/dev-agent/upload-file", summary="上传文件到开发代理")
async def upload_file(file: UploadFile = File(...)):
    try:
        # 验证文件类型
        if not file.filename.lower().endswith('.pdf'):
            return {"code": 400, "msg": "只支持PDF文件上传", "data": {}}
        
        # 生成时间戳文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file.filename)[1]
        new_filename = f"{timestamp}{file_extension}"
        
        # 保存文件
        file_path = os.path.join(UPLOAD_DIR, new_filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        return {
            "code": 200,
            "msg": "文件上传成功",
            "data": {
                "filename": new_filename
            }
        }
    except Exception as e:
        return {"code": 500, "msg": f"文件上传失败: {str(e)}", "data": {}}

# 爬虫接口
@app.post("/api/crawler/crawl", summary="启动爬虫")
def crawl_endpoint(req: CrawlRequest):
    try:
        crawl_state = CrawlState(seed_url=req.seed_url)
        result = crawler_graph.invoke(crawl_state)
        return {"code": 200, "msg": "爬取完成", "data": result}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}


# 健康检查接口
@app.get("/api/health", summary="服务健康检查")
def health_check():
    return {"code": 200, "msg": "service is running"}

# Root route to serve the main frontend page
@app.get("/", response_class=HTMLResponse, summary="访问前端页面")
async def serve_frontend():
    ui_index_path = os.path.join(os.path.dirname(__file__), "..", "ui", "index.html")
    if os.path.exists(ui_index_path):
        with open(ui_index_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    else:
        return HTMLResponse(content="<h1>Frontend not found</h1><p>Please ensure the UI files are in the ui directory.</p>", status_code=404)

# Admin page route
@app.get("/admin", response_class=HTMLResponse, summary="访问管理页面")
async def serve_admin_page():
    admin_path = os.path.join(os.path.dirname(__file__), "..", "ui", "admin.html")
    if os.path.exists(admin_path):
        with open(admin_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    else:
        return HTMLResponse(content="<h1>Admin page not found</h1>", status_code=404)

# Robot development page route
@app.get("/robot-dev", response_class=HTMLResponse, summary="访问客服机器人开发页面")
async def serve_robot_dev_page():
    robot_dev_path = os.path.join(os.path.dirname(__file__), "..", "ui", "robot-dev.html")
    if os.path.exists(robot_dev_path):
        with open(robot_dev_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    else:
        return HTMLResponse(content="<h1>Robot development page not found</h1>", status_code=404)

# Serve static files (CSS, JS, images, etc.)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "ui")), name="static")