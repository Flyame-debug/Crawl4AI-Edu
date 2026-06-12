@echo off
echo 正在停止所有后端服务...

taskkill /f /im "python.exe" 2>nul
taskkill /f /im "celery.exe" 2>nul
taskkill /f /im "redis-server.exe" 2>nul
taskkill /f /im "minio.exe" 2>nul

echo 所有服务已停止！
pause