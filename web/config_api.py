from fastapi import APIRouter, Body
from pydantic import BaseModel
from core.common.config_manager import ConfigManager
from typing import Optional
import json


# 创建路由实例
config_router = APIRouter(prefix="/api/config", tags=["config"])

# 配置请求模型
class KnowledgeBaseUrlRequest(BaseModel):
    url: str


@config_router.get("/knowledge-base-url", response_model=dict)
def get_knowledge_base_config():
    """
    获取知识库配置
    """
    try:
        url = ConfigManager.get_knowledge_base_url()
        return {"code": 200, "msg": "success", "data": {"url": url}}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}


@config_router.post("/knowledge-base-url", response_model=dict)
def update_knowledge_base_config(req: KnowledgeBaseUrlRequest):
    """
    更新知识库配置
    """
    try:
        url = req.url
        ConfigManager.set_knowledge_base_url(url)
        return {"code": 200, "msg": "配置更新成功", "data": {}}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}