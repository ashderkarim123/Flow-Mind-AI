@echo off
echo ==============================================
echo   STARTING FLOWMIND AI (FINAL VERSION)
echo ==============================================

echo [1/2] Starting Python Backend...
start cmd /k "cd backend && python run.py"

echo [2/2] Starting Next.js Frontend...
start cmd /k "npm run dev -- -p 3005"

echo ==============================================
echo Both servers are starting in separate windows.
echo Please wait a moment, then open:
echo http://localhost:3005
echo ==============================================
pause
