@echo off
setlocal
set "ARQ=%~dp0backup_associacao.txt"
if not exist "%ARQ%" (
  echo Nao encontrei o backup da associacao anterior.
  echo ^(talvez voce nunca tenha associado o .py a este programa^)
  pause
  exit /b 1
)
set /p ANTIGO=<"%ARQ%"
if "%ANTIGO%"=="NAO_HAVIA" (
  reg delete "HKCU\Software\Classes\.py" /f >nul 2>&1
  echo A associacao com .py foi removida ^(nao havia nada definido antes^).
) else (
  reg add "HKCU\Software\Classes\.py" /ve /d "%ANTIGO%" /f >nul
  echo A associacao com .py foi restaurada para: %ANTIGO%
)
echo.
pause
