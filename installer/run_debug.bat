@echo off
cd /d "%~dp0\.."
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app\main.py
) else (
  py -3 app\main.py
)
echo.
echo AI Director kapandi. Hata varsa yukarida gorunur.
pause
