@echo off
REM Batch script to set up virtual environment for MCP JSON-RPC Registry

echo Setting up virtual environment for MCP JSON-RPC Registry...

REM Check if Python 3.13+ is available
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR_VERSION=%%a
    set MINOR_VERSION=%%b
)

if %MAJOR_VERSION% LSS 3 (
    echo Error: Python 3.13 or higher is required.
    echo Current version: %PYTHON_VERSION%
    pause
    exit /b 1
)

if %MAJOR_VERSION% EQU 3 if %MINOR_VERSION% LSS 13 (
    echo Error: Python 3.13 or higher is required.
    echo Current version: %PYTHON_VERSION%
    pause
    exit /b 1
)

echo Python version: %PYTHON_VERSION%

REM Create virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists.
)

REM Activate virtual environment and install dependencies
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Install development dependencies if available
if exist "requirements-dev.txt" (
    echo Installing development dependencies...
    pip install -r requirements-dev.txt
)

echo.
echo Virtual environment setup complete!
echo To activate the virtual environment in the future, run:
echo   venv\Scripts\activate.bat
echo.
echo To run the application, make sure the virtual environment is activated and run:
echo   python -m src.registry.main --transport streamable-http --port 8080
echo.
pause