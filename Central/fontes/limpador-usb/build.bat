@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Gerando LimpadorUSB.exe

rem ------------------------------------------------------------------
rem  Gera os executaveis do Limpador USB (Windows 64 e 32 bits).
rem  Uso:  build.bat           -> x64 e ia32
rem        build.bat x64       -> somente 64 bits
rem        build.bat ia32      -> somente 32 bits
rem  Requisito: Node.js 18+ instalado (https://nodejs.org)
rem ------------------------------------------------------------------

where node >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Node.js nao encontrado. Instale em https://nodejs.org e rode de novo.
  pause & exit /b 1
)

set "ARCH=--x64 --ia32"
if /i "%~1"=="x64"  set "ARCH=--x64"
if /i "%~1"=="ia32" set "ARCH=--ia32"

echo.
echo [1/3] Instalando dependencias...
if exist package-lock.json (call npm ci) else (call npm install)
if errorlevel 1 goto :falha

echo.
echo [2/3] Compilando a interface React...
call npx vite build
if errorlevel 1 goto :falha

echo.
echo [3/3] Gerando o executavel...
if exist release rmdir /s /q release
call npx electron-builder --win portable %ARCH% --publish never
if errorlevel 1 goto :falha

echo.
echo ===== Pronto! Executaveis em: %cd%\release =====
dir /b release\*.exe
echo.
pause
exit /b 0

:falha
echo.
echo [ERRO] A geracao falhou. Veja as mensagens acima.
pause
exit /b 1
