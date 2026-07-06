@echo off
rem Rapport hebdo de maturation -> Telegram (dimanche 20h)
cd /d C:\Users\sam\trading
set PYTHONUTF8=1
set PY=C:\Users\samue\AppData\Local\Programs\Python\Python313\python.exe
"%PY%" maturation_report.py send >> maturation.log 2>&1
