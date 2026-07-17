@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Installazione - Assegnazione OEPAC
cd /d "%~dp0"

echo ============================================================
echo    ASSEGNAZIONE AUTOMATICA OEPAC
echo    Installazione dei componenti su questo PC
echo    Linee Guida DGC Roma Capitale n. 260/2024
echo ============================================================
echo.
echo Questo programma installa tutto il necessario (Python e i
echo componenti dell'applicazione) e crea i collegamenti per
echo avviare il gestionale con un doppio clic.
echo Alla prima esecuzione puo' richiedere qualche minuto.
echo.

REM Pacchetto offline presente? (cartella "offline" con i componenti)
set "OFFLINE=0"
if exist "%~dp0offline\wheels" set "OFFLINE=1"
if "%OFFLINE%"=="1" echo [i] Rilevato pacchetto OFFLINE: installazione senza internet.
echo.

REM ------------------------------------------------------------
REM  1) Individua o installa Python
REM ------------------------------------------------------------
set "PYCMD="
call :trova_python
if defined PYCMD goto python_ok

echo [1/4] Python non presente: installazione automatica in corso...

REM 1a) dal pacchetto offline
if "%OFFLINE%"=="1" (
    set "PYSETUP="
    for %%F in ("%~dp0offline\python-*.exe") do set "PYSETUP=%%~fF"
    if defined PYSETUP (
        echo       Installazione di Python dal pacchetto offline...
        "!PYSETUP!" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0 Include_pip=1
        goto dopo_python_install
    )
)

REM 1b) tramite winget (App Installer, presente su Windows 10/11)
where winget >nul 2>&1
if not !errorlevel! == 0 goto python_org_download
echo       Installazione di Python tramite winget...
winget install -e --id Python.Python.3.12 --scope user --silent --accept-source-agreements --accept-package-agreements
set "WINGET_RC=!errorlevel!"
call :aggiorna_path
call :trova_python
if defined PYCMD goto python_ok
if "!WINGET_RC!"=="0" goto dopo_python_install
echo       Installazione tramite winget non riuscita: provo il download da python.org...

:python_org_download
REM 1c) download dell'installer ufficiale da python.org
echo       Download di Python 3.12 da python.org...
set "PYURL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
set "PYSETUP=%TEMP%\oepac-python-setup.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri '%PYURL%' -OutFile '%PYSETUP%' } catch { exit 1 }"
if not exist "%PYSETUP%" (
    call :errore "Impossibile scaricare Python. Verifica la connessione a internet oppure usa il pacchetto offline (vedi README)."
    goto fine_errore
)
echo       Installazione di Python...
"%PYSETUP%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0 Include_pip=1

:dopo_python_install
REM Il PATH non e' aggiornato nella sessione corrente: lo rileggo dal registro
call :aggiorna_path
call :trova_python
if not defined PYCMD (
    echo.
    echo [i] Python e' stato installato ma non e' ancora visibile in questa
    echo     finestra. Chiudi questa finestra e riesegui "Installa-OEPAC.bat":
    echo     al secondo avvio l'installazione prosegue e si completa da sola.
    echo.
    pause
    exit /b 0
)

:python_ok
echo [1/4] Python: OK
echo.

REM ------------------------------------------------------------
REM  2) Ambiente virtuale dedicato
REM ------------------------------------------------------------
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [2/4] Creazione dell'ambiente dedicato...
    call :crea_venv
)
if not exist "%~dp0.venv\Scripts\python.exe" (
    call :errore "Creazione dell'ambiente virtuale non riuscita."
    goto fine_errore
)
echo [2/4] Ambiente dedicato: OK
echo.

set "VPY=%~dp0.venv\Scripts\python.exe"

REM ------------------------------------------------------------
REM  3) Componenti dell'applicazione
REM ------------------------------------------------------------
echo [3/4] Installazione dei componenti dell'applicazione...
if not "%OFFLINE%"=="1" "%VPY%" -m pip install --upgrade pip >nul 2>&1
if "%OFFLINE%"=="1" (
    "%VPY%" -m pip install --no-index --find-links "%~dp0offline\wheels" -r "%~dp0requirements.txt"
) else (
    "%VPY%" -m pip install -r "%~dp0requirements.txt"
)
if !errorlevel! neq 0 (
    call :errore "Installazione dei componenti non riuscita. Verifica la connessione a internet."
    goto fine_errore
)
copy /y "%~dp0requirements.txt" "%~dp0.venv\.req_installed" >nul
echo [3/4] Componenti: OK
echo.

REM ------------------------------------------------------------
REM  4) Collegamenti su Desktop e Menu Start
REM ------------------------------------------------------------
echo [4/4] Creazione dei collegamenti...
call :crea_collegamenti
echo [4/4] Collegamenti: OK
echo.

echo ============================================================
echo    INSTALLAZIONE COMPLETATA
echo ============================================================
echo.
echo Da ora puoi avviare il gestionale con il collegamento
echo "Assegnazione OEPAC" presente sul Desktop e nel Menu Start.
echo.
choice /C SN /N /M "Vuoi avviare subito il gestionale adesso? [S=si / N=no] "
if !errorlevel! == 1 (
    echo.
    echo Avvio in corso...
    start "" "%~dp0Avvia-OEPAC.bat"
)
exit /b 0

REM ============================================================
REM  Subroutine
REM ============================================================

:trova_python
REM Imposta PYCMD se trova un Python utilizzabile. In modalita' offline le
REM wheel sono compilate per Python 3.12: si accetta solo un interprete 3.12,
REM altrimenti si procede a installare quello incluso nel pacchetto.
set "PYCMD="
if "%OFFLINE%"=="1" goto trova_python_312
py -3 -c "import sys" >nul 2>&1 && set "PYCMD=py -3"
if defined PYCMD goto :eof
python -c "import sys" >nul 2>&1 && set "PYCMD=python"
if defined PYCMD goto :eof
for /d %%D in ("%LocalAppData%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" set "PYCMD=%%D\python.exe"
)
goto :eof

:trova_python_312
REM Offline: le wheel sono per Python 3.12 -> serve esattamente 3.12
py -3.12 -c "import sys" >nul 2>&1 && set "PYCMD=py -3.12"
if defined PYCMD goto :eof
for /d %%D in ("%LocalAppData%\Programs\Python\Python312*") do (
    if exist "%%D\python.exe" set "PYCMD=%%D\python.exe"
)
goto :eof

:aggiorna_path
REM Rilegge il PATH utente dal registro (aggiornato dall'installer di Python)
set "USERPATH="
for /f "usebackq tokens=2,*" %%A in (`reg query "HKCU\Environment" /v PATH 2^>nul`) do set "USERPATH=%%B"
if defined USERPATH set "PATH=%PATH%;%USERPATH%"
goto :eof

:crea_venv
REM Crea l'ambiente virtuale gestendo sia "py -3" sia un percorso con spazi.
REM Se PYCMD contiene un backslash e' un percorso -> va quotato.
if not "!PYCMD:\=!"=="!PYCMD!" (
    "!PYCMD!" -m venv "%~dp0.venv"
) else (
    !PYCMD! -m venv "%~dp0.venv"
)
goto :eof

:crea_collegamenti
set "LAUNCH=%~dp0Avvia-OEPAC.bat"
set "ICON=%~dp0oepac.ico"
if not exist "%ICON%" set "ICON=%SystemRoot%\System32\shell32.dll,21"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; foreach($dir in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))){ if($dir){ $lnk=Join-Path $dir 'Assegnazione OEPAC.lnk'; $s=$w.CreateShortcut($lnk); $s.TargetPath=$env:LAUNCH; $s.WorkingDirectory=(Split-Path $env:LAUNCH); $s.IconLocation=$env:ICON; $s.Description='Assegnazione automatica OEPAC - DGC 260/2024'; $s.Save() } }"
goto :eof

:errore
echo.
echo [ERRORE] %~1
echo.
goto :eof

:fine_errore
pause
exit /b 1
