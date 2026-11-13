@echo off
chcp 65001 >nul
title Editor de Fotos - gerar executavel
cd /d "%~dp0"

where npm >nul 2>nul
if errorlevel 1 (
  echo.
  echo O Node.js nao esta instalado.
  echo Baixe a versao LTS em https://nodejs.org , instale e rode este arquivo de novo.
  echo.
  pause
  exit /b 1
)

echo.
echo [1/2] Instalando dependencias, pode demorar alguns minutos na primeira vez...
call npm install
if errorlevel 1 goto erro

echo.
echo [2/2] Gerando o executavel...
call npm run build:win
if errorlevel 1 goto erro

echo.
echo Pronto! O instalador e a versao portatil estao na pasta "dist".
start "" "%~dp0dist"
pause
exit /b 0

:erro
echo.
echo Algo deu errado. Veja as mensagens acima.
pause
exit /b 1
