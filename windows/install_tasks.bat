@echo off
rem ═══ Installation des tâches planifiées du Prime Engine (lancer en admin) ═══

rem 1. Watcher : au démarrage de la machine, relance auto si crash
schtasks /Create /F /TN "Prime Watcher" /SC ONSTART /RU "%USERNAME%" ^
  /TR "C:\Users\sam\trading\windows\start_watcher.bat"

rem 2. Watchdog : toutes les 15 minutes
schtasks /Create /F /TN "Prime Watchdog" /SC MINUTE /MO 15 ^
  /TR "C:\Users\sam\trading\windows\run_watchdog.bat"

rem 3. Chercheur nocturne : 23h30
schtasks /Create /F /TN "Prime Research Nightly" /SC DAILY /ST 23:30 ^
  /TR "C:\Users\sam\trading\windows\run_nightly.bat"

rem 4. Data lake : refresh quotidien 07h00 (via le .bat : chemin python complet +
rem    PYTHONUTF8, comme les autres tâches, le `python` nu échouait sous SYSTEM)
schtasks /Create /F /TN "Prime Datalake" /SC DAILY /ST 07:00 ^
  /TR "C:\Users\sam\trading\windows\run_datalake.bat"

rem 5. Rapport hebdo de maturation -> Telegram : dimanche 20h00
schtasks /Create /F /TN "Prime Maturation" /SC WEEKLY /D SUN /ST 20:00 ^
  /TR "C:\Users\sam\trading\windows\run_maturation.bat"

rem 6. Signal hebdo SWING ACTIONS (achat/vente) -> Telegram : lundi 14h00
schtasks /Create /F /TN "Prime Swing" /SC WEEKLY /D MON /ST 14:00 ^
  /TR "C:\Users\sam\trading\windows\run_swing.bat"

echo.
echo Taches installees. Demarrer le watcher maintenant :
echo   schtasks /Run /TN "Prime Watcher"
