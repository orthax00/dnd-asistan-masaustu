@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python bulunamadi. https://www.python.org/downloads/ adresinden kur ve "Add to PATH" kutusunu isaretle.
  pause
  exit /b 1
)
if not exist .venv (
  echo Ilk kurulum yapiliyor, biraz surebilir...
  py -3 -m venv .venv || (pause & exit /b 1)
  .venv\Scripts\python -m pip install --upgrade pip >nul
)
.venv\Scripts\python -m pip install -q -r requirements.txt || (pause & exit /b 1)
start "" .venv\Scripts\pythonw.exe main.py
