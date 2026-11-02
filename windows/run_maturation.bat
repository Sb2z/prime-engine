@echo off
rem Rapport hebdo de maturation -> Telegram (dimanche 20h)
cd /d "%~dp0.."
set PYTHONUTF8=1
set PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
"%PY%" maturation_report.py send >> maturation.log 2>&1
