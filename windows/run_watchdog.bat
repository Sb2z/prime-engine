@echo off
cd /d C:\Users\sam\trading
set PYTHONUTF8=1
set PY=C:\Users\samue\AppData\Local\Programs\Python\Python313\python.exe
"%PY%" watchdog.py >> watchdog.log 2>&1
