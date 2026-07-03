@echo off
cd /d D:\robot-grinding-knowledge
echo Starting RGKB Server...
echo.
echo   Main:      http://localhost:8765
echo   Dashboard: http://localhost:8765/dashboard/
echo.
start http://localhost:8765
py -3 pipeline_server.py
echo.
echo [Server stopped]
pause
