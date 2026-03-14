from fastapi import APIRouter, Body
from pydantic import BaseModel
from core.crawl.graph import crawler_graph
from core.crawl.state import CrawlState
from core.common.db import db_query, db_execute
from core.common.config_manager import ConfigManager
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
        
        # 更新知识库URL配置
        ConfigManager.set_knowledge_base_url(req.url)
        
        return {"code": 200, "msg": "知识库创建成功", "data": result}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}


@kb_router.put("/{kb_id}", response_model=dict)
def update_knowledge_base(kb_id: str, req: UpdateKnowledgeBaseRequest):
    """
    更新知识库URL，根据rebuild参数决定是否重新爬取新URL的内容
    """
    try:
        # 检查知识库ID是否存在
        existing_record = db_query("SELECT id, seed_url FROM crawler_results WHERE id = ?", (kb_id,))
        if not existing_record or len(existing_record) == 0:
            return {"code": 404, "msg": "知识库不存在", "data": {}}
        
        old_url = existing_record[0][1]
        new_url = req.url
        
        # 如果URL没有变化，直接返回成功
        if old_url == new_url:
            return {"code": 200, "msg": "知识库URL未变化，无需更新", "data": {}}
        
        # 更新知识库URL配置
        ConfigManager.set_knowledge_base_url(new_url)
        
        # 如果不需要重建，直接返回成功
        if not req.rebuild:
            # 更新数据库中的seed_url，但保留其他数据
            db_execute("UPDATE crawler_results SET seed_url = ? WHERE id = ?", (new_url, kb_id))
            return {"code": 200, "msg": "知识库URL已更新，但未重新爬取", "data": {}}
        
        # 需要重建，重新爬取新URL的内容
        print(f"URL changed from {old_url} to {new_url}, starting new crawl...")
        crawl_state = CrawlState(seed_url=new_url)
        result = crawler_graph.invoke(crawl_state)
        
        # 删除旧URL的所有相关记录
        db_execute("DELETE FROM crawler_results WHERE seed_url = ?", (old_url,))
        
        return {"code": 200, "msg": "知识库URL已更新并重新爬取完成", "data": result}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}


@kb_router.delete("/{kb_id}", response_model=dict)
def delete_knowledge_base(kb_id: str):
    """
    删除知识库
    """
    try:
        # 删除知识库记录
        db_execute("DELETE FROM crawler_results WHERE id = ?", (kb_id,))
        
        # 清空知识库URL配置
        ConfigManager.set_knowledge_base_url("")
        
        return {"code": 200, "msg": "知识库删除成功", "data": {}}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}


@kb_router.post("/rebuild/{kb_id}", response_model=dict)
def rebuild_knowledge_base(kb_id: str):
    """
    手动重建指定知识库（重新爬取）
    """
    try:
        # 获取知识库的seed_url
        existing_record = db_query("SELECT seed_url FROM crawler_results WHERE id = ?", (kb_id,))
        if not existing_record or len(existing_record) == 0:
            return {"code": 404, "msg": "知识库不存在", "data": {}}
        
        seed_url = existing_record[0][0]
        
        # 重新爬取
        crawl_state = CrawlState(seed_url=seed_url)
        result = crawler_graph.invoke(crawl_state)
        
        return {"code": 200, "msg": "知识库重建完成", "data": result}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}


@kb_router.post("/rebuild-current", response_model=dict)
def rebuild_current_knowledge_base():
    """
    重建当前知识库：读取配置表中的知识库URL，然后重新爬取对应的页面
    """
    try:
        # 获取配置中的知识库URL
        url = ConfigManager.get_knowledge_base_url()
        
        if not url:
            return {"code": 400, "msg": "没有配置的知识库URL", "data": {}}
        
        # 清空现有的爬虫结果
        db_execute("DELETE FROM crawler_results")
        
        # 重新爬取URL
        crawl_state = CrawlState(seed_url=url)
        result = crawler_graph.invoke(crawl_state)
        
        return {"code": 200, "msg": "成功重建知识库", "data": result}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}