@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m pip install -r requirements-dev.txt
python -m PyInstaller --noconfirm --onedir --noconsole --name DemandaWhatsApp main.py
echo.
echo Pronto: dist\DemandaWhatsApp\DemandaWhatsApp.exe
pause
