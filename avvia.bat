@echo off
title Assegnazione OEPAC - Avvio
echo.
echo ========================================================
echo    Assegnazione automatica OEPAC - DGC 260/2024
echo ========================================================
echo.

cd /d "%~dp0"

where py >nul 2>&1
if %ERRORLEVEL% == 0 (
    set PYTHON_CMD=py
    goto found_python
)
where python >nul 2>&1
if %ERRORLEVEL% == 0 (
    set PYTHON_CMD=python
    goto found_python
)

echo [ERRORE] Python non trovato.
echo Scarica Python da: https://www.python.org/downloads/
echo IMPORTANTE: spunta "Add Python to PATH" durante l'installazione.
pause
exit /b 1

:found_python

if not exist "venv\Scripts\python.exe" (
    echo [*] Prima esecuzione: creazione ambiente virtuale...
    %PYTHON_CMD% -m venv venv
    if not exist "venv\Scripts\python.exe" (
        echo [ERRORE] Impossibile creare l'ambiente virtuale.
        pause
        exit /b 1
    )
    echo [*] Installazione dipendenze...
    "venv\Scripts\pip.exe" install -q -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERRORE] Installazione dipendenze fallita.
        pause
        exit /b 1
    )
    copy /y requirements.txt venv\.req_installed >nul
    echo [OK] Ambiente pronto.
    goto start_app
)

fc /b requirements.txt venv\.req_installed >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [*] Aggiornamento dipendenze...
    "venv\Scripts\pip.exe" install -q -r requirements.txt
    copy /y requirements.txt venv\.req_installed >nul
)

:start_app
echo [*] Avvio applicazione...
start "" http://localhost:8501
"venv\Scripts\streamlit.exe" run app.py --server.headless true --server.port 8501
pause
