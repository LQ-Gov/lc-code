from fastapi import APIRouter, Body
from pydantic import BaseModel
from core.common.db import db_query, db_execute
from typing import List, Optional


# 创建路由实例
sf_router = APIRouter(prefix="/api/special-flows", tags=["special_flows"])

# 特殊问题流程请求模型
class SpecialFlowRequest(BaseModel):
    key: str
    desc: str
    prompt: str
    status: str = "active"


class UpdateSpecialFlowRequest(BaseModel):
    desc: str
    prompt: str
    status: str = "active"


# 特殊问题流程响应模型
class SpecialFlow(BaseModel):
    key: str
    desc: str
    flow: str
    status: str
    prompt: str


@sf_router.get("", response_model=dict)
def get_special_flows():
    """
    获取所有特殊问题流程
    """
    try:
        sql = "SELECT key, desc, flow, status, prompt FROM specific_question_flows"
        results = db_query(sql)
        flows = []
        for result in results:
            flow = {
                "key": result[0],
                "desc": result[1],
                "flow": result[2],
                "status": result[3],
                "prompt": result[4] or ""
            }
            flows.append(flow)
        return {"code": 200, "msg": "success", "data": flows}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": []}


@sf_router.post("", response_model=dict)
def create_special_flow(req: SpecialFlowRequest):
    """
    创建特殊问题流程
    """
    try:
        db_execute(
            "INSERT INTO specific_question_flows (key, desc, flow, status, prompt) VALUES (?, ?, ?, ?, ?)",
            (req.key, req.desc, "", req.status, req.prompt)
        )
        return {"code": 200, "msg": "特殊问题流程创建成功", "data": {}}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}


@sf_router.put("/{key}", response_model=dict)
def update_special_flow(key: str, req: UpdateSpecialFlowRequest):
    """
    更新特殊问题流程
    """
    try:
        db_execute(
            "UPDATE specific_question_flows SET desc = ?, flow = ?, status = ?, prompt = ? WHERE key = ?",
            (req.desc, "", req.status, req.prompt, key)
        )
        return {"code": 200, "msg": "特殊问题流程更新成功", "data": {}}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}


@sf_router.delete("/{key}", response_model=dict)
def delete_special_flow(key: str):
    """
    删除特殊问题流程
    """
    try:
        db_execute("DELETE FROM specific_question_flows WHERE key = ?", (key,))
        return {"code": 200, "msg": "特殊问题流程删除成功", "data": {}}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": {}}