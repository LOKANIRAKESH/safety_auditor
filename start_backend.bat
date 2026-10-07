@echo off
echo Starting ICS Safety Auditor API...
echo.
echo  Backend: http://localhost:8000
echo  Swagger: http://localhost:8000/docs
echo.
cd /d %~dp0
uvicorn backend.main:app --reload --port 8000 --host 0.0.0.0
