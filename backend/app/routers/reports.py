"""报表统计接口"""
import json
from collections import defaultdict

from fastapi import APIRouter, HTTPException

from .. import database as db

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _load_run(run_id: int) -> dict:
    run = db.query_one("SELECT * FROM runs WHERE id=?", (run_id,))
    if not run:
        raise HTTPException(404, "测试不存在")
    return run


def _model_suite_scores(run_id: int) -> tuple[dict, dict, list]:
    """返回 (model_map, suite_map, rows)，其中 rows 为评分明细"""
    run = _load_run(run_id)
    model_ids = json.loads(run["model_ids"])
    suite_ids = json.loads(run["suite_ids"])
    models = {
        m["id"]: m
        for m in db.query(
            f"SELECT * FROM models WHERE id IN ({','.join('?' * len(model_ids))})",
            tuple(model_ids),
        )
    }
    suites = {
        s["id"]: s
        for s in db.query(
            f"SELECT * FROM suites WHERE id IN ({','.join('?' * len(suite_ids))})",
            tuple(suite_ids),
        )
    }
    rows = db.query(
        "SELECT * FROM run_results WHERE run_id=?", (run_id,)
    )
    return models, suites, rows


def _compute_scores(models: dict, suites: dict, rows: list[dict]) -> list[dict]:
    """按模型×题库聚合平均分（0-100）"""
    agg: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["max_score"] and r["score"] is not None:
            agg[r["model_id"]][r["suite_id"]].append(r["score"] / r["max_score"])
    result = []
    for mid, model in models.items():
        entry = {"model_id": mid, "model_name": model["display_name"] or model["name"], "suites": {}, "overall": None}
        suite_scores = []
        for sid, suite in suites.items():
            vals = agg[mid][sid]
            if vals:
                s = round(sum(vals) / len(vals) * 100, 1)
                entry["suites"][suite["key"]] = {
                    "suite_id": sid,
                    "suite_name": suite["name"],
                    "score": s,
                    "answered": len(vals),
                }
                suite_scores.append(s)
        entry["overall"] = round(sum(suite_scores) / len(suite_scores), 1) if suite_scores else None
        result.append(entry)
    result.sort(key=lambda x: -(x["overall"] or 0))
    return result


@router.get("/leaderboard")
def leaderboard(run_id: int):
    models, suites, rows = _model_suite_scores(run_id)
    scores = _compute_scores(models, suites, rows)
    rank = 1
    for i, s in enumerate(scores):
        if i > 0 and (s["overall"] or 0) < (scores[i - 1]["overall"] or 0):
            rank = i + 1
        s["rank"] = rank
    return scores


@router.get("/radar")
def radar(run_id: int):
    models, suites, rows = _model_suite_scores(run_id)
    scores = _compute_scores(models, suites, rows)
    suite_keys = [s["key"] for s in suites.values()]
    series = []
    for s in scores:
        series.append(
            {
                "name": s["model_name"],
                "values": [s["suites"].get(k, {}).get("score", 0) for k in suite_keys],
            }
        )
    return {"suites": list(suites.values()), "series": series}


@router.get("/compare")
def compare(run_id: int):
    """模型差距分析：两两之间的总平均分差值矩阵"""
    models, suites, rows = _model_suite_scores(run_id)
    scores = _compute_scores(models, suites, rows)
    names = [s["model_name"] for s in scores]
    overalls = [s["overall"] or 0 for s in scores]
    matrix = []
    for i, row_name in enumerate(names):
        line = []
        for j in range(len(names)):
            line.append(round(overalls[i] - overalls[j], 1))
        matrix.append({"name": row_name, "diffs": line})
    return {"names": names, "matrix": matrix}


@router.get("/trend")
def trend(model_id: int, suite_key: str | None = None, limit: int = 50):
    """某模型在各轮测试中的分数走势"""
    runs = db.query(
        """SELECT r.* FROM runs r
           WHERE r.status='completed' AND r.model_ids LIKE ?
           ORDER BY r.id DESC LIMIT ?""",
        (f"%{model_id}%", limit),
    )
    suite_row = (
        db.query_one("SELECT * FROM suites WHERE key=?", (suite_key,)) if suite_key else None
    )
    points = []
    for run in reversed(runs):
        rows = db.query(
            "SELECT * FROM run_results WHERE run_id=? AND model_id=?",
            (run["id"], model_id),
        )
        if suite_row:
            vals = [
                r["score"] / r["max_score"]
                for r in rows
                if r["suite_id"] == suite_row["id"] and r["max_score"]
            ]
            score = round(sum(vals) / len(vals) * 100, 1) if vals else None
        else:
            vals = [r["score"] / r["max_score"] for r in rows if r["max_score"]]
            score = round(sum(vals) / len(vals) * 100, 1) if vals else None
        points.append(
            {
                "run_id": run["id"],
                "run_name": run["name"],
                "created_at": run["created_at"],
                "score": score,
            }
        )
    return points
