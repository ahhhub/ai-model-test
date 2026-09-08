"""模型管理接口"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import database as db
from ..services import llm

router = APIRouter(prefix="/api/models", tags=["models"])


class ModelIn(BaseModel):
    name: str
    display_name: str
    base_url: str = ""
    api_key: str = ""
    disable_thinking: bool = True


@router.get("")
def list_models():
    return db.query("SELECT * FROM models ORDER BY id")


@router.post("")
def add_model(payload: ModelIn):
    mid = db.execute(
        "INSERT INTO models(name,display_name,base_url,api_key,disable_thinking,created_at) VALUES(?,?,?,?,?,?)",
        (
            payload.name.strip(),
            payload.display_name.strip(),
            payload.base_url.strip(),
            payload.api_key.strip(),
            1 if payload.disable_thinking else 0,
            db.now(),
        ),
    )
    return db.query_one("SELECT * FROM models WHERE id=?", (mid,))


@router.put("/{model_id}")
def update_model(model_id: int, payload: ModelIn):
    exists = db.query_one("SELECT id FROM models WHERE id=?", (model_id,))
    if not exists:
        raise HTTPException(404, "模型不存在")
    db.execute(
        "UPDATE models SET name=?, display_name=?, base_url=?, api_key=?, disable_thinking=? WHERE id=?",
        (
            payload.name.strip(),
            payload.display_name.strip(),
            payload.base_url.strip(),
            payload.api_key.strip(),
            1 if payload.disable_thinking else 0,
            model_id,
        ),
    )
    return db.query_one("SELECT * FROM models WHERE id=?", (model_id,))


@router.delete("/{model_id}")
def delete_model(model_id: int):
    db.execute("DELETE FROM models WHERE id=?", (model_id,))
    return {"ok": True}


@router.post("/{model_id}/test")
async def test_connectivity(model_id: int):
    """连通性测试：发送一条简短消息"""
    model = db.query_one("SELECT * FROM models WHERE id=?", (model_id,))
    if not model:
        raise HTTPException(404, "模型不存在")
    text, latency, error = await llm.chat_once(model, [{"role": "user", "content": "请回复：pong"}])
    if error:
        return {"ok": False, "latency_ms": round(latency, 1), "reply": "", "error": error}
    return {"ok": True, "latency_ms": round(latency, 1), "reply": text[:200], "error": ""}
