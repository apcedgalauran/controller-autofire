@echo off
title Controller Autofire - Setup
echo ============================================
echo  Controller Autofire - one-time setup
echo  Approve any Windows / installer prompts.
echo ============================================
echo.
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install it from python.org, tick "Add to PATH", then run this again.
  pause
  exit /b 1
)
echo [1/3] Installing Python packages...
python -m pip install --upgrade vgamepad XInput-Python
echo.
echo [2/3] Installing ViGEmBus virtual controller driver...
winget install --id ViGEm.ViGEmBus -e
echo.
echo [3/3] Installing HidHide (hides your real controller from games)...
winget install --id Nefarius.HidHide -e
echo.
echo ============================================
echo  Done. RESTART your PC, then set up HidHide
echo  (see "READ ME.txt").
echo ============================================
pause
