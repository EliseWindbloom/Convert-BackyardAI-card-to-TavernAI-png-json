@echo off
setlocal

echo Converting BackyardAI card to TavernAI format...
echo Full path: %*

rem Call Python script with the exact command line arguments
python "%~dp0backyard_to_tavern.py" %*

echo.
echo Press any key to exit...
pause >nul
