"""FastAPI 入口"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import database
from .config import FRONTEND_DIST, IMAGES_DIR
from .routers import models, reports, runs, suites

database.init_db()

app = FastAPI(title="AI 模型评测平台", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models.router)
app.include_router(suites.router)
app.include_router(runs.router)
app.include_router(reports.router)

# 本地图片库（前端预览与人工查看用）
if IMAGES_DIR.exists():
    app.mount("/api/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")


@app.get("/api/health")
def health():
    return {"ok": True}


# 生产模式：直接托管前端构建产物
_dist = Path(FRONTEND_DIST)
if _dist.exists():
    assets = _dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/")
    def index():
        return FileResponse(_dist / "index.html")

    @app.get("/{path:path}")
    def spa_fallback(path: str):
        candidate = _dist / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
