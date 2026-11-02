@echo off
cd /d "%~dp0.."
set PYTHONUTF8=1
set PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
"%PY%" watchdog.py >> watchdog.log 2>&1
