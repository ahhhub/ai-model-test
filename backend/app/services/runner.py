"""测试运行引擎：后台异步执行整轮评测"""
import asyncio
import json
import logging
import traceback

from .. import database as db
from . import frontend, judge, llm, scorers

logger = logging.getLogger("runner")

# run_id -> asyncio.Event，用于停止信号
_stop_flags: dict[int, asyncio.Event] = {}


def request_stop(run_id: int) -> None:
    if run_id in _stop_flags:
        _stop_flags[run_id].set()


async def _task_wrapper(run_id: int) -> None:
    """异常兜底：任何异常都要把 run 标记为 failed"""
    try:
        await run_execute(run_id)
    except Exception:  # noqa: BLE001
        logger.error("run %s failed:\n%s", run_id, traceback.format_exc())
        db.execute(
            "UPDATE runs SET status='failed', finished_at=? WHERE id=?",
            (db.now(), run_id),
        )
        _stop_flags.pop(run_id, None)


async def start_run(run_id: int) -> None:
    _stop_flags[run_id] = asyncio.Event()
    asyncio.create_task(_task_wrapper(run_id))


def _is_image_error(error: str) -> bool:
    """判断错误是否与图片下载/加载有关（仅对带备用地址的图片题触发重试）"""
    low = (error or "").lower()
    if "image" in low or "图片" in error:
        return any(k in low for k in ("download", "403", "failed", "load", "loading", "无法", "下载", "失败"))
    # 图片题上出现 403/下载类错误，同样视为图片问题
    if "403" in low or "forbidden" in low:
        return "url" in low or "http" in low
    return any(k in low for k in ("failed to download", "下载失败", "download failed"))


async def run_execute(run_id: int) -> None:
    stop_event = _stop_flags.get(run_id, asyncio.Event())
    run = db.query_one("SELECT * FROM runs WHERE id=?", (run_id,))
    if not run:
        return
    model_ids = json.loads(run["model_ids"])
    suite_ids = json.loads(run["suite_ids"])
    models = [db.query_one("SELECT * FROM models WHERE id=?", (mid,)) for mid in model_ids]
    models = [m for m in models if m]
    suites = [db.query_one("SELECT * FROM suites WHERE id=?", (sid,)) for sid in suite_ids]
    suites = [s for s in suites if s]
    judge_model = db.query_one("SELECT * FROM models WHERE id=?", (run["judge_model_id"],)) if run.get("judge_model_id") else None
    diff = (run.get("difficulty") or "").strip()

    # 统计任务总量并入库
    total = 0
    work_items = []
    for model in models:
        for suite in suites:
            if diff:
                questions = db.query(
                    "SELECT * FROM questions WHERE suite_id=? AND difficulty=? ORDER BY id",
                    (suite["id"], diff),
                )
            else:
                questions = db.query(
                    "SELECT * FROM questions WHERE suite_id=? ORDER BY id", (suite["id"],)
                )
            for q in questions:
                work_items.append((model, suite, q))
                total += 1
    db.execute("UPDATE runs SET status='running', total=? WHERE id=?", (total, run_id))

    done = 0
    # 按 4 个并发执行
    sem = asyncio.Semaphore(4)

    async def work(model, suite, q):
        nonlocal done
        async with sem:
            if stop_event.is_set():
                return
            messages = llm.build_messages(q)
            answer, latency, error, usage = await llm.chat_once(model, messages)
            backup_used = False
            if error and q.get("image_url_backup") and _is_image_error(error):
                q2 = dict(q)
                q2["image_url"] = q2["image_url_backup"]
                answer, latency, error, usage = await llm.chat_once(model, llm.build_messages(q2))
                backup_used = not error
            score, detail = 0.0, ""
            max_score = q.get("max_score") or 1
            if error:
                detail = error
            else:
                if q.get("judge"):
                    if judge_model:
                        score, detail = await judge.judge_answer(judge_model, q, answer)
                    else:
                        detail = "未配置裁判模型，无法自动评分"
                elif q.get("answer_type") == "html":
                    score, detail = await frontend.score_html(answer, q, judge_model)
                else:
                    score, detail = scorers.score_objective(answer, q)
            if backup_used and not error:
                detail = (detail + "（已切换备用图片地址）").strip()
            output_tokens = (usage or {}).get("completion_tokens")
            db.execute(
                """INSERT INTO run_results
                   (run_id, model_id, suite_id, question_id, answer, score, max_score, latency_ms, output_tokens, error, detail)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    model["id"],
                    suite["id"],
                    q["id"],
                    (answer or "")[:20000],
                    score,
                    max_score,
                    round(latency, 1) if latency is not None else None,
                    output_tokens,
                    error or "",
                    detail or "",
                ),
            )
            done += 1
            db.execute("UPDATE runs SET done=? WHERE id=?", (done, run_id))

    await asyncio.gather(*(work(m, s, q) for m, s, q in work_items))

    if stop_event.is_set():
        db.execute(
            "UPDATE runs SET status='stopped', finished_at=? WHERE id=?",
            (db.now(), run_id),
        )
    else:
        db.execute(
            "UPDATE runs SET status='completed', done=total, finished_at=? WHERE id=?",
            (db.now(), run_id),
        )
    _stop_flags.pop(run_id, None)
