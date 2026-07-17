@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
title Assegnazione OEPAC
cd /d "%~dp0"

REM Se l'ambiente non e' ancora installato, avvia l'installazione guidata
if not exist "%~dp0.venv\Scripts\streamlit.exe" (
    echo L'applicazione non e' ancora installata su questo PC.
    echo Avvio dell'installazione guidata...
    echo.
    call "%~dp0Installa-OEPAC.bat"
    exit /b 0
)

REM Aggiorna i componenti solo se requirements.txt e' cambiato
if exist "%~dp0.venv\.req_installed" (
    fc /b "%~dp0requirements.txt" "%~dp0.venv\.req_installed" >nul 2>&1
    if errorlevel 1 (
        echo Aggiornamento dei componenti in corso...
        "%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
        copy /y "%~dp0requirements.txt" "%~dp0.venv\.req_installed" >nul
    )
)

echo ============================================================
echo    ASSEGNAZIONE OEPAC - avvio in corso
echo ============================================================
echo.
echo Tra pochi secondi si aprira' automaticamente il browser su:
echo    http://localhost:8501
echo Se non si apre da solo, apri il browser e scrivi quell'indirizzo.
echo.
echo Per CHIUDERE l'applicazione, chiudi questa finestra nera.
echo ============================================================
echo.

set "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false"

REM Apre il browser appena il server e' pronto (attende la porta 8501)
start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "for($i=0;$i -lt 60;$i++){ try { $c=New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',8501); $c.Close(); Start-Process 'http://localhost:8501'; break } catch { Start-Sleep -Milliseconds 500 } }"

"%~dp0.venv\Scripts\streamlit.exe" run "%~dp0app.py" --server.headless=true --server.port=8501

echo.
echo Applicazione terminata. Puoi chiudere questa finestra.
pause >nul
