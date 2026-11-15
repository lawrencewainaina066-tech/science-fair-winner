@echo off
setlocal
cd /d "%~dp0.."

echo ==========================================
echo       SCIENCE FAIR WINNER (SFW)
echo          Windows Installer
echo ==========================================
echo.

if not exist "requirements.txt" (
    echo ERROR: requirements.txt was not found.
    echo Please extract the entire ZIP file before running this installer.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    py -m venv .venv
    if errorlevel 1 (
        echo Could not create virtual environment. Check that Python is installed.
        pause
        exit /b 1
    )
)

echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error

echo Installing SFW dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

if not exist ".env" copy ".env.example" ".env" >nul

echo.
echo Starting Science Fair Winner...
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto :error
goto :eof

:error
echo.
echo Installation or launch failed. Read the error above.
pause
exit /b 1
