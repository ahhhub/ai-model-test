@echo off
chcp 65001 >nul
cd /d "%~dp0frontend"
echo 启动前端开发服务器: http://127.0.0.1:5173 （需后端已在 8000 端口运行）
npm run dev
pause
