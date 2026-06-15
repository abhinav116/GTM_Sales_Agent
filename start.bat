@echo off
echo Starting RAAPID Sales Intelligence Agent...
echo.
echo Backend  : http://localhost:8000
echo Frontend : http://localhost:5173
echo.

start "RAAPID Backend" cmd /k "cd /d "%~dp0" && python -X utf8 -m uvicorn backend:app --reload --port 8000"
timeout /t 2 /nobreak > nul
start "RAAPID Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Both servers started. Open http://localhost:5173 in your browser.
