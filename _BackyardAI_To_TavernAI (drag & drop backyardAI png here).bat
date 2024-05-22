@echo off
setlocal enabledelayedexpansion

REM Check if an argument was provided
if "%~1"=="" (
    echo Drag and drop an input png file onto this batch file.
    pause
    exit /b 1
)

cd /d %~dp0

python "convert_backyard_to_tavern_v4.py" %1
