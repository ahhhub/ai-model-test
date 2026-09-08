@echo off
chcp 65001 >nul
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
    echo [1/5] 创建虚拟环境...
    python -m venv .venv
)

echo [2/5] 安装后端依赖...
.venv\Scripts\python -m pip install -q -r requirements.txt

if not exist "%USERPROFILE%\AppData\Local\ms-playwright\chromium_headless_shell*" (
    echo [3/5] 首次运行：下载无头浏览器（前端代码实测需要，约 300MB）...
    set "PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/"
    .venv\Scripts\python -m playwright install chromium
) else (
    echo [3/5] 无头浏览器已就绪
)

if not exist "..\frontend\dist\index.html" (
    echo [4/5] 首次运行：构建前端页面...
    pushd "..\frontend"
    if not exist "node_modules" call npm install --no-fund --no-audit
    call npm run build
    popd
) else (
    echo [4/5] 前端页面已就绪
)

echo [5/5] 启动服务: http://127.0.0.1:8000
start "" http://127.0.0.1:8000
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
