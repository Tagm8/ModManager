@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=python"

where %PYTHON% >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python 3 is not installed or isn't in PATH.
    echo Install Python 3 from https://www.python.org/downloads/
    echo Make sure "Add Python to PATH" is enabled.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo [SA Mod Manager] Creating Python virtual environment...
    
    if exist ".venv" (
        rmdir /s /q ".venv"
    )

    %PYTHON% -m venv .venv

    if errorlevel 1 (
        echo.
        echo ERROR: Python could not create the virtual environment.
        echo.
        echo Try reinstalling Python 3 with the standard installation options.
        echo Make sure Python and venv support are installed.
        echo.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

python -m pip install --upgrade pip

python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install Python requirements.
    echo.
    pause
    exit /b 1
)

python sa_mod_manager.py

if errorlevel 1 (
    echo.
    echo SA Mod Manager exited with an error.
    echo.
    pause
    exit /b 1
)

endlocal
