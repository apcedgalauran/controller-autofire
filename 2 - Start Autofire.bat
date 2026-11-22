@echo off
title Controller Autofire
cd /d "%~dp0"
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
