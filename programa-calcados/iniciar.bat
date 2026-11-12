@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv (
  echo Preparando o programa pela primeira vez, aguarde...
  python -m venv .venv || (echo Instale o Python 3.11 ou mais novo em python.org & pause & exit /b 1)
  call .venv\Scripts\activate.bat
  python -m pip install --quiet --upgrade pip
  pip install --quiet -r requirements.txt || (echo Falha ao instalar. Verifique a internet. & pause & exit /b 1)
) else (
  call .venv\Scripts\activate.bat
)
python -m app.main
if errorlevel 1 pause
