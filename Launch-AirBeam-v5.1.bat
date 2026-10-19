@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

set "PY_EXE="

if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\pythonw.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\pythonw.exe"
) else (
    where pythonw.exe >nul 2>&1
    if not errorlevel 1 (
        set "PY_EXE=pythonw.exe"
    ) else (
        where pyw.exe >nul 2>&1
        if not errorlevel 1 (
            set "PY_EXE=pyw.exe"
        ) else (
            where python.exe >nul 2>&1
            if not errorlevel 1 (
                set "PY_EXE=python.exe"
            ) else (
                set "PY_EXE=py.exe"
            )
        )
    )
)

start "" "%PY_EXE%" "%~dp0desktop-sender\sender.py" %*
exit
