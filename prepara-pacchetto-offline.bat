@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Pacchetto OFFLINE - Assegnazione OEPAC
cd /d "%~dp0"

echo ============================================================
echo    PREPARAZIONE PACCHETTO OFFLINE
echo    (Python + componenti, per installare senza internet)
echo ============================================================
echo.
echo Esegui questo passaggio UNA SOLA VOLTA, su un PC CON internet.
echo Al termine, copia l'INTERA cartella del gestionale su una
echo chiavetta USB: sui PC senza internet bastera' eseguire
echo "Installa-OEPAC.bat" (rilevera' il pacchetto offline da solo).
echo.
pause

REM Serve un Python su questo PC per scaricare i componenti
set "PYCMD="
py -3 -c "import sys" >nul 2>&1 && set "PYCMD=py -3"
if not defined PYCMD (
    python -c "import sys" >nul 2>&1 && set "PYCMD=python"
)
if not defined PYCMD (
    echo.
    echo [ERRORE] Su questo PC non e' presente Python.
    echo Esegui prima "Installa-OEPAC.bat" su questo PC, poi riprova.
    echo.
    pause
    exit /b 1
)

if not exist "%~dp0offline\wheels" mkdir "%~dp0offline\wheels"

echo.
echo [1/2] Download dei componenti dell'applicazione (wheel Windows)...
!PYCMD! -m pip download -r "%~dp0requirements.txt" --dest "%~dp0offline\wheels" --only-binary=:all: --platform win_amd64 --python-version 312 --implementation cp
if !errorlevel! neq 0 (
    echo.
    echo [ERRORE] Download dei componenti non riuscito.
    echo.
    pause
    exit /b 1
)

echo.
echo [2/2] Download dell'installer di Python 3.12...
set "PYURL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri '%PYURL%' -OutFile '%~dp0offline\python-3.12.10-amd64.exe' } catch { exit 1 }"
if not exist "%~dp0offline\python-3.12.10-amd64.exe" (
    echo.
    echo [ERRORE] Download dell'installer di Python non riuscito.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo    PACCHETTO OFFLINE PRONTO (cartella "offline")
echo ============================================================
echo.
echo Copia l'intera cartella del gestionale sui PC di destinazione
echo ed esegui "Installa-OEPAC.bat": non servira' internet.
echo.
pause
