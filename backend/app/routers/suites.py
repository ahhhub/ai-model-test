"""题库与题目管理接口"""
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import database as db

router = APIRouter(prefix="/api", tags=["suites"])


@router.get("/suites")
def list_suites():
    suites = db.query("SELECT * FROM suites ORDER BY sort_order, id")
    # 每个题库的难度分布
    dist_rows = db.query(
        "SELECT suite_id, difficulty, COUNT(*) AS c FROM questions GROUP BY suite_id, difficulty"
    )
    dist: dict[int, dict[str, int]] = {}
    for r in dist_rows:
        dist.setdefault(r["suite_id"], {})[r["difficulty"]] = r["c"]
    for s in suites:
        s["difficulty_counts"] = dist.get(s["id"], {})
        s["question_count"] = sum(s["difficulty_counts"].values())
    return suites


@router.get("/suites/{suite_id}/questions")
def list_questions(suite_id: int):
    questions = db.query(
        "SELECT * FROM questions WHERE suite_id=? ORDER BY id", (suite_id,)
    )
    for q in questions:
        q["options"] = json.loads(q.get("options") or "[]")
        q["expected"] = json.loads(q.get("expected") or "[]")
        q["test_harness"] = json.loads(q.get("test_harness") or "[]")
    return questions


class QuestionIn(BaseModel):
    title: str = ""
    prompt: str
    image_url: str = ""
    answer_type: str = "text"  # choice / number / text / code
    options: list[str] = []
    expected: list[str] = []
    test_harness: list = []
    judge: bool = False
    max_score: float = 1
    rubric: str = ""
    reference: str = ""
    difficulty: str = "easy"


@router.post("/suites/{suite_id}/questions")
def add_question(suite_id: int, payload: QuestionIn):
    suite = db.query_one("SELECT id FROM suites WHERE id=?", (suite_id,))
    if not suite:
        raise HTTPException(404, "题库不存在")
    diff = payload.difficulty if payload.difficulty in db.DIFFICULTY_LEVELS else "easy"
    qid = db.execute(
        """INSERT INTO questions
           (suite_id,title,prompt,image_url,answer_type,options,expected,test_harness,rubric,reference,judge,max_score,difficulty)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            suite_id,
            payload.title.strip(),
            payload.prompt,
            payload.image_url.strip(),
            payload.answer_type,
            json.dumps(payload.options, ensure_ascii=False),
            json.dumps(payload.expected, ensure_ascii=False),
            json.dumps(payload.test_harness, ensure_ascii=False),
            payload.rubric,
            payload.reference,
            1 if payload.judge else 0,
            payload.max_score,
            diff,
        ),
    )
    return db.query_one("SELECT * FROM questions WHERE id=?", (qid,))


@router.delete("/questions/{question_id}")
def delete_question(question_id: int):
    db.execute("DELETE FROM questions WHERE id=?", (question_id,))
    return {"ok": True}
