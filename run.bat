@echo off
REM Universal run script for Windows

echo Amazon Product Research API
echo ============================
echo.

REM Check if .env exists
if not exist .env (
    echo Creating .env file...
    echo OPENAI_API_KEY=your_openai_api_key_here > .env
    echo.
    echo WARNING: Please edit .env file and add your OpenAI API key!
    echo.
    pause
    notepad .env
)

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed
    echo Please install Docker Desktop from: https://docs.docker.com/desktop/install/windows-install/
    pause
    exit /b 1
)

REM Check if container is running
docker-compose ps | findstr "Up" >nul 2>&1
if not errorlevel 1 (
    echo Container is already running
    echo.
    echo Choose an option:
    echo 1^) Restart
    echo 2^) Stop
    echo 3^) View logs
    echo 4^) Rebuild
    set /p choice="Enter choice (1-4): "
    
    if "%choice%"=="1" (
        echo Restarting...
        docker-compose restart
    ) else if "%choice%"=="2" (
        echo Stopping...
        docker-compose down
        exit /b 0
    ) else if "%choice%"=="3" (
        echo Viewing logs (Ctrl+C to exit)...
        docker-compose logs -f
        exit /b 0
    ) else if "%choice%"=="4" (
        echo Rebuilding...
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
    )
) else (
    echo Starting Docker container...
    docker-compose up -d --build
)

echo.
echo Application is running!
echo.
echo Open: http://localhost:8000
echo.
echo To view logs: docker-compose logs -f
echo To stop: docker-compose down
echo.
pause
