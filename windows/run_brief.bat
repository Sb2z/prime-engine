@echo off
rem ── Briefing de tendance (signal-only), 5x/jour, lancé par le Planificateur ──
cd /d "%~dp0.."
set PYTHONUTF8=1
set PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
"%PY%" market_brief.py >> market_brief.log 2>&1
