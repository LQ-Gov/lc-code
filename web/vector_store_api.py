"""
向量库API模块
提供构建向量库和相似性搜索的HTTP接口
"""
from fastapi import APIRouter, Query, Body
from typing import List, Dict, Optional
from pydantic import BaseModel
from core.common.vector_store import KnowledgeBaseVectorStore

# 创建路由实例
vs_router = APIRouter(prefix="/api/vector-store", tags=["vector_store"])

class BuildVectorStoreRequest(BaseModel):
    force_rebuild: bool = False

class SearchRequest(BaseModel):
    query: str
    n_results: int = 5

class SearchResultItem(BaseModel):
    question: str
    answer: str
    url: str
    distance: Optional[float] = None

class SearchResponse(BaseModel):
    code: int
    msg: str
    data: List[SearchResultItem]

@vs_router.post("/build", response_model=dict)
def build_vector_store(req: BuildVectorStoreRequest = BuildVectorStoreRequest()):
    """
    构建向量库，将知识库数据导入Chroma
    """
    try:
        vector_store = KnowledgeBaseVectorStore()
        count = vector_store.build_vector_store(force_rebuild=req.force_rebuild)
        return {
            "code": 200,
            "msg": f"向量库构建成功，共导入 {count} 个QA对",
            "data": {"count": count}
        }
    except Exception as e:
        return {
            "code": 500,
            "msg": f"构建向量库失败: {str(e)}",
            "data": {}
        }

@vs_router.get("/info", response_model=dict)
def get_vector_store_info():
    """
    获取向量库信息
    """
    try:
        vector_store = KnowledgeBaseVectorStore()
        info = vector_store.get_collection_info()
        return {
            "code": 200,
            "msg": "获取向量库信息成功",
            "data": info
        }
    except Exception as e:
        return {
            "code": 500,
            "msg": f"获取向量库信息失败: {str(e)}",
            "data": {}
        }

@vs_router.post("/search", response_model=SearchResponse)
def search_similar_questions(req: SearchRequest):
    """
    搜索与查询最相似的问题
    """
    try:
        vector_store = KnowledgeBaseVectorStore()
        results = vector_store.search_similar_questions(
            query=req.query,
            n_results=req.n_results
        )
        
        # 转换为Pydantic模型
        result_items = []
        for item in results:
            result_items.append(SearchResultItem(**item))
        
        return SearchResponse(
            code=200,
            msg="搜索成功",
            data=result_items
        )
    except Exception as e:
        return SearchResponse(
            code=500,
            msg=f"搜索失败: {str(e)}",
            data=[]
        )