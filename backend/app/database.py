"""SQLite 数据访问层（线程安全）"""
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from .config import DATA_DIR, DB_PATH, QUESTIONS_DIR

_lock = threading.RLock()


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _lock, get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                base_url TEXT NOT NULL DEFAULT '',
                api_key TEXT NOT NULL DEFAULT '',
                disable_thinking INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS suites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                sort_order INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suite_id INTEGER NOT NULL,
                title TEXT DEFAULT '',
                prompt TEXT NOT NULL,
                image_url TEXT DEFAULT '',
                answer_type TEXT NOT NULL DEFAULT 'text',
                options TEXT DEFAULT '',
                expected TEXT DEFAULT '',
                test_harness TEXT DEFAULT '',
                rubric TEXT DEFAULT '',
                reference TEXT DEFAULT '',
                judge INTEGER DEFAULT 0,
                max_score REAL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                model_ids TEXT NOT NULL,
                suite_ids TEXT NOT NULL,
                judge_model_id INTEGER,
                status TEXT DEFAULT 'pending',
                total INTEGER DEFAULT 0,
                done INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                finished_at TEXT
            );
            CREATE TABLE IF NOT EXISTS run_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                model_id INTEGER NOT NULL,
                suite_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                answer TEXT,
                score REAL,
                max_score REAL,
                latency_ms REAL,
                error TEXT,
                detail TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_results_run ON run_results(run_id);
            """
        )
        # 老库迁移：models 表补充 disable_thinking 列
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(models)").fetchall()}
        if "disable_thinking" not in cols:
            conn.execute("ALTER TABLE models ADD COLUMN disable_thinking INTEGER NOT NULL DEFAULT 1")
    seed_questions()
    migrate_questions()


# ---------------- 题库种子数据 ----------------

def seed_questions() -> None:
    """首次启动时把 questions/*.json 灌入数据库"""
    with _lock, get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM suites").fetchone()["c"]
        if count > 0:
            return
    if not QUESTIONS_DIR.exists():
        return
    for f in sorted(QUESTIONS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        suite = data.get("suite", {})
        questions = data.get("questions", [])
        if not suite or not questions:
            continue
        with _lock, get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO suites(key,name,category,description,sort_order) VALUES(?,?,?,?,?)",
                (
                    suite.get("key"),
                    suite.get("name"),
                    suite.get("category"),
                    suite.get("description", ""),
                    suite.get("sort_order", 0),
                ),
            )
            suite_id = cur.lastrowid
            for q in questions:
                conn.execute(
                    """INSERT INTO questions
                       (suite_id,title,prompt,image_url,answer_type,options,expected,
                        test_harness,rubric,reference,judge,max_score)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        suite_id,
                        q.get("title", ""),
                        q.get("prompt", ""),
                        q.get("image_url", ""),
                        q.get("answer_type", "text"),
                        json.dumps(q.get("options", []), ensure_ascii=False),
                        json.dumps(q.get("expected", []), ensure_ascii=False),
                        json.dumps(q.get("test_harness", []), ensure_ascii=False),
                        q.get("rubric", ""),
                        q.get("reference", ""),
                        1 if q.get("judge") else 0,
                        q.get("max_score", 1),
                    ),
                )


def migrate_questions() -> None:
    """增量迁移：把题库 JSON 中新增的题目补入既有数据库。

    按「题库 key + 题目 prompt 全文」去重，已存在的题目（含用户在网页里
    自定义添加的题目）全部保留，只插入新增题目，幂等可重复执行。
    """
    if not QUESTIONS_DIR.exists():
        return
    for f in sorted(QUESTIONS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        suite = data.get("suite", {})
        questions = data.get("questions", [])
        if not suite or not questions:
            continue
        suite_row = query_one("SELECT id FROM suites WHERE key=?", (suite.get("key"),))
        if not suite_row:
            continue
        suite_id = suite_row["id"]
        # 同步题库名称与描述
        execute(
            "UPDATE suites SET name=?, description=? WHERE id=?",
            (suite.get("name"), suite.get("description", ""), suite_id),
        )
        existing = {
            r["prompt"]
            for r in query("SELECT prompt FROM questions WHERE suite_id=?", (suite_id,))
        }
        new_items = [q for q in questions if q.get("prompt") not in existing]
        if not new_items:
            continue
        params: list[tuple] = []
        for q in new_items:
            params.append(
                (
                    suite_id,
                    q.get("title", ""),
                    q.get("prompt", ""),
                    q.get("image_url", ""),
                    q.get("answer_type", "text"),
                    json.dumps(q.get("options", []), ensure_ascii=False),
                    json.dumps(q.get("expected", []), ensure_ascii=False),
                    json.dumps(q.get("test_harness", []), ensure_ascii=False),
                    q.get("rubric", ""),
                    q.get("reference", ""),
                    1 if q.get("judge") else 0,
                    q.get("max_score", 1),
                )
            )
        executemany(
            """INSERT INTO questions
               (suite_id,title,prompt,image_url,answer_type,options,expected,
                test_harness,rubric,reference,judge,max_score)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            params,
        )


# ---------------- 通用查询辅助 ----------------

def query(sql: str, params: tuple = ()) -> list[dict]:
    with _lock, get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    with _lock, get_conn() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def execute(sql: str, params: tuple = ()) -> int:
    """执行写操作，返回 lastrowid"""
    with _lock, get_conn() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid


def executemany(sql: str, params: list[tuple]) -> None:
    with _lock, get_conn() as conn:
        conn.executemany(sql, params)
