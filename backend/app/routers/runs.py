"""测试运行接口"""
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import database as db
from ..services import runner

router = APIRouter(prefix="/api/runs", tags=["runs"])


class RunIn(BaseModel):
    name: str
    model_ids: list[int]
    suite_ids: list[int]
    judge_model_id: int | None = None
    difficulty: str = ""


@router.get("")
def list_runs():
    return db.query("SELECT * FROM runs ORDER BY id DESC LIMIT 100")


@router.post("")
async def create_run(payload: RunIn):
    if not payload.model_ids:
        raise HTTPException(400, "请至少选择一个参与模型")
    if not payload.suite_ids:
        raise HTTPException(400, "请至少选择一个测试项目")
    diff = payload.difficulty.strip()
    if diff and diff not in db.DIFFICULTY_LEVELS:
        raise HTTPException(400, "无效的难度等级")
    for mid in payload.model_ids:
        if not db.query_one("SELECT id FROM models WHERE id=?", (mid,)):
            raise HTTPException(404, f"模型 {mid} 不存在")
    for sid in payload.suite_ids:
        if not db.query_one("SELECT id FROM suites WHERE id=?", (sid,)):
            raise HTTPException(404, f"题库 {sid} 不存在")
    if payload.judge_model_id and not db.query_one(
        "SELECT id FROM models WHERE id=?", (payload.judge_model_id,)
    ):
        raise HTTPException(404, "裁判模型不存在")
    run_id = db.execute(
        "INSERT INTO runs(name,model_ids,suite_ids,judge_model_id,difficulty,status,total,done,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (
            payload.name.strip() or f"评测 {db.now()}",
            json.dumps(payload.model_ids),
            json.dumps(payload.suite_ids),
            payload.judge_model_id,
            diff,
            "pending",
            0,
            0,
            db.now(),
        ),
    )
    await runner.start_run(run_id)
    return db.query_one("SELECT * FROM runs WHERE id=?", (run_id,))


@router.get("/{run_id}")
def get_run(run_id: int):
    run = db.query_one("SELECT * FROM runs WHERE id=?", (run_id,))
    if not run:
        raise HTTPException(404, "测试不存在")
    return run


@router.post("/{run_id}/stop")
def stop_run(run_id: int):
    run = db.query_one("SELECT id,status FROM runs WHERE id=?", (run_id,))
    if not run:
        raise HTTPException(404, "测试不存在")
    runner.request_stop(run_id)
    if run["status"] in ("pending", "running"):
        db.execute(
            "UPDATE runs SET status='stopped', finished_at=? WHERE id=?",
            (db.now(), run_id),
        )
    return {"ok": True}


@router.delete("/{run_id}")
def delete_run(run_id: int):
    runner.request_stop(run_id)
    db.execute("DELETE FROM run_results WHERE run_id=?", (run_id,))
    db.execute("DELETE FROM runs WHERE id=?", (run_id,))
    return {"ok": True}


@router.get("/{run_id}/results")
def get_results(run_id: int):
    """按模型×题库聚合 + 明细"""
    run = db.query_one("SELECT * FROM runs WHERE id=?", (run_id,))
    if not run:
        raise HTTPException(404, "测试不存在")
    model_ids = json.loads(run["model_ids"])
    suite_ids = json.loads(run["suite_ids"])
    models = {m["id"]: m for m in db.query(f"SELECT * FROM models WHERE id IN ({','.join('?'*len(model_ids))})", tuple(model_ids))}
    suites = {s["id"]: s for s in db.query(f"SELECT * FROM suites WHERE id IN ({','.join('?'*len(suite_ids))})", tuple(suite_ids))}
    rows = db.query("SELECT * FROM run_results WHERE run_id=? ORDER BY id", (run_id,))
    return {
        "run": run,
        "models": list(models.values()),
        "suites": list(suites.values()),
        "results": rows,
    }
