@echo off
chcp 65001 > nul
title Crawl4AI 后端启动器

echo ========================================
echo   Crawl4AI 后端服务启动
echo ========================================
echo.

REM 1. 激活虚拟环境
call venv\Scripts\activate
echo [1/5] 虚拟环境已激活

REM 2. 启动Redis（如果没有Redis，跳过）
start "Redis" cmd /c "redis-server" 2>nul
echo [2/5] Redis 已启动

REM 3. 启动MinIO（如果没有MinIO，跳过）
start "MinIO" cmd /c "minio.exe server D:\minio_data --console-address ':9001'" 2>nul
echo [3/5] MinIO 已启动

REM 4. 启动Django
start "Django" cmd /c "cd src\backend && python manage.py runserver"
echo [4/5] Django 启动中... http://127.0.0.1:8000

REM 5. 启动Celery Worker
start "Celery Worker" cmd /c "cd src\backend && celery -A edu_backend worker -l info"
echo [5/5] Celery Worker 启动中...

echo.
echo ========================================
echo   启动完成！
echo   Django: http://127.0.0.1:8000/admin/
echo   MinIO:  http://127.0.0.1:9001
echo ========================================
echo.
echo 按任意键关闭此窗口（不会停止服务）
pause > nul