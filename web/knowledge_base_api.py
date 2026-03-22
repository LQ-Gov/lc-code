from fastapi import APIRouter, Body
from pydantic import BaseModel
from core.common.knowledge_service import KnowledgeBaseService
from typing import List, Optional
import json


# 创建路由实例
kb_router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge_bases"])

# 知识库请求模型
class KnowledgeBaseRequest(BaseModel):
    url: str


class UpdateKnowledgeBaseRequest(BaseModel):
    url: str
    rebuild: bool = False  # 新增参数，控制是否重建


# 知识库响应模型
class KnowledgeBase(BaseModel):
    id: str
    seed_url: str
    current_url: str
    raw_content: Optional[str] = None
    questions: Optional[str] = None
    answers: Optional[str] = None
    created_at: str


@kb_router.get("", response_model=dict)
def get_knowledge_bases():
    """
    获取所有知识库，包含所有字段
    """
    try:
        knowledge_bases = KnowledgeBaseService.get_all_knowledge_bases()
        return {"code": 200, "msg": "success", "data": knowledge_bases}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": []}

@kb_router.delete("/{kb_id}", response_model=dict)
def delete_knowledge_base(kb_id: str):
    """
    删除知识库
    """
    try:
        success = KnowledgeBaseService.delete_knowledge_base(kb_id)
        if success:
            return {"code": 200, "msg": "知识库删除成功", "data": {}}
        else:
            return {"code": 500, "msg": "删除知识库失败", "data": {}}
    except Exception as e:
        if "知识库不存在" in str(e):
            return {"code": 404, "msg": str(e), "data": {}}
        return {"code": 500, "msg": str(e), "data": {}}


@kb_router.post("/rebuild/{kb_id}", response_model=dict)
def rebuild_knowledge_base(kb_id: str):
    """
    手动重建指定知识库（重新爬取）
    """
    try:
        result = KnowledgeBaseService.rebuild_knowledge_base(kb_id)
        return {"code": 200, "msg": "知识库重建任务已启动", "data": result}
    except Exception as e:
        if "知识库不存在" in str(e):
            return {"code": 404, "msg": str(e), "data": {}}
        return {"code": 500, "msg": str(e), "data": {}}


@kb_router.post("/rebuild-current", response_model=dict)
def rebuild_current_knowledge_base():
    """
    重建当前知识库：读取配置表中的知识库URL，然后重新爬取对应的页面
    """
    try:
        result = KnowledgeBaseService.rebuild_current_knowledge_base()
        return {"code": 200, "msg": "成功重建知识库", "data": result}
    except Exception as e:
        if "没有配置的知识库URL" in str(e):
            return {"code": 400, "msg": str(e), "data": {}}
        return {"code": 500, "msg": str(e), "data": {}}