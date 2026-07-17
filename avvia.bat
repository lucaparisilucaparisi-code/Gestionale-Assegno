@echo off
REM ------------------------------------------------------------
REM  Avvio del gestionale OEPAC (compatibilita').
REM  Alla PRIMA esecuzione installa automaticamente tutti i
REM  componenti necessari (Python compreso); dalle volte
REM  successive avvia direttamente l'applicazione.
REM  Per un'installazione "pulita" con collegamenti sul Desktop
REM  usa "Installa-OEPAC.bat".
REM ------------------------------------------------------------
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\streamlit.exe" (
    call "%~dp0Avvia-OEPAC.bat"
) else (
    call "%~dp0Installa-OEPAC.bat"
)
