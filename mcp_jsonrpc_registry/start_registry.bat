@echo off
REM Batch script to start the MCP JSON-RPC Registry

echo Starting MCP JSON-RPC Registry...

REM Check if virtual environment exists
if not exist "venv" (
    echo Error: Virtual environment not found.
    echo Please run setup_env.bat first to create the virtual environment.
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if required packages are installed
python -c "import mcp" 2>nul
if errorlevel 1 (
    echo Required packages not found in virtual environment.
    echo Running setup script to install dependencies...
    call setup_env.bat
    call venv\Scripts\activate.bat
)

REM Start the registry server
echo Starting registry server...
echo Use Ctrl+C to stop the server
python -m src.registry.main --transport streamable-http --port 8080

echo Registry server stopped.
pause