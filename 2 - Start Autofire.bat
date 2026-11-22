@echo off
title Autofire Launcher
cd /d "%~dp0"

rem Close any copy of the app that is already running, so the newest version opens
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*autofire*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>nul

rem Install anything missing
python -c "import XInput, vgamepad" >nul 2>nul
if errorlevel 1 (
  echo Installing missing parts, one moment...
  echo If a ViGEmBus installer pops up, click through it and finish it.
  echo.
  python -m pip install vgamepad XInput-Python
  echo.
)

python autofire_gui.py
exit
