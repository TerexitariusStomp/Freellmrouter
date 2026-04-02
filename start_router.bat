@echo off
cd /d "%~dp0hermes_free_router"
start "FreeRouter Proxy" python -m app.main --mode proxy --host 127.0.0.1 --port 8000
echo FreeRouter Proxy started at http://127.0.0.1:8000
echo Press any key to exit this window...
pause >nul
