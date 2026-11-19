@echo off
rem MetreToit - double-cliquez sur ce fichier (Windows) pour ouvrir l interface de test.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Premiere utilisation : installation ^(1 a 3 minutes^)...
  py -3 -m venv .venv || python -m venv .venv
  .venv\Scripts\pip install -q -r requirements.txt
)
start "" http://localhost:5000
.venv\Scripts\python interface.py
pause
