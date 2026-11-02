@echo off
rem ── Refresh quotidien du data lake (07h00), lancé en SYSTEM ──
cd /d "%~dp0.."
set PYTHONUTF8=1
set PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
"%PY%" research\datalake.py refresh >> research\datalake.log 2>&1
