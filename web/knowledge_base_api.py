from fastapi import APIRouter, Body
from pydantic import BaseModel
from core.crawl.graph import crawler_graph
from core.crawl.state import CrawlState
from core.common.db import db_query, db_execute
from typing import List, Optional
import json


# 创建路由实例
kb_router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge_bases"])

# 知识库请求模型
class KnowledgeBaseRequest(BaseModel):
    url: str


class UpdateKnowledgeBaseRequest(BaseModel):
    url: str


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
        # 查询所有爬虫结果记录
        sql = """
            SELECT 
                id,
                seed_url,
                current_url,
                raw_content,
                questions,
                answers,
                created_at
            FROM crawler_results
            ORDER BY created_at DESC
        """
        results = db_query(sql)
        knowledge_bases = []
        for result in results:
            kb = {
                "id": str(result[0]) if result[0] else "",
                "seed_url": result[1] if result[1] else "",
                "current_url": result[2] if result[2] else "",
                "raw_content": result[3] if result[3] else "",
                "questions": result[4] if result[4] else "",
                "answers": result[5] if result[5] else "",
                "created_at": result[6] if result[6] else ""
            }
            knowledge_bases.append(kb)
        return {"code": 200, "msg": "success", "data": knowledge_bases}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": []}


@kb_router.post("", response_model=dict)
def create_knowledge_base(req: KnowledgeBaseRequest):
    """
    创建知识库并启动爬虫
    """
    try:
        # 启动爬虫更新知识库
        crawl_state = CrawlState(seed_url=req.url)
        result = crawler_graph.invoke(crawl_state)
        
        return {"code": 200, "msg": "知识库创建成功", "data": result}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}


@kb_router.put("/{kb_id}", response_model=dict)
def update_knowledge_base(kb_id: str, req: UpdateKnowledgeBaseRequest):
    """
    更新知识库，如果URL改变则重新爬取
    """
    try:
        # 检查旧URL是否与新URL不同
        old_data = db_query("SELECT seed_url FROM crawler_results WHERE id = ?", (kb_id,))
        if old_data and len(old_data) > 0 and old_data[0][0] != req.url:
            # URL发生了变化，启动爬虫重新获取数据
            crawl_state = CrawlState(seed_url=req.url)
            result = crawler_graph.invoke(crawl_state)
            
            # 删除旧的爬取结果
            db_execute("DELETE FROM crawler_results WHERE seed_url = ?", (old_data[0][0],))
        
        # 更新数据库中的URL
        db_execute(
            "UPDATE crawler_results SET seed_url = ? WHERE id = ?",
            (req.url, kb_id)
        )
        return {"code": 200, "msg": "知识库更新成功", "data": {}}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}


@kb_router.delete("/{kb_id}", response_model=dict)
def delete_knowledge_base(kb_id: str):
    """
    删除知识库
    """
    try:
        db_execute("DELETE FROM crawler_results WHERE id = ?", (kb_id,))
        return {"code": 200, "msg": "知识库删除成功", "data": {}}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}