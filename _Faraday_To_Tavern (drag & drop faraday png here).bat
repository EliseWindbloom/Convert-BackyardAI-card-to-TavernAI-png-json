@echo off
setlocal enabledelayedexpansion

REM Check if an argument was provided
if "%~1"=="" (
    echo Drag and drop an input png file onto this batch file.
    pause
    exit /b
)

REM Set the input file path
set "input_file=%~1"

cd /d %~dp0

python "convert_faraday_to_tavern_v2.py" "!input_file!"