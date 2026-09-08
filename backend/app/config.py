"""全局配置"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
QUESTIONS_DIR = DATA_DIR / "questions"
STATIC_DIR = BASE_DIR / "static"
FRONTEND_DIST = BASE_DIR.parent.parent / "frontend" / "dist"

DB_PATH = DATA_DIR / "app.db"

# 并发控制
MAX_CONCURRENT_REQUESTS = int(os.getenv("AI_MAX_CONCURRENT", "6"))
REQUEST_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT", "120"))
