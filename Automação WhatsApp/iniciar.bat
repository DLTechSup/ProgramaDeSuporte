@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul || (echo Python 3.11+ nao encontrado. Instale em python.org & pause & exit /b 1)
python -c "import PySide6" 2>nul || python -m pip install -r requirements.txt
python main.py
if errorlevel 1 pause
