@echo off
:: ========================================================
:: AirBeam - Microsoft KM-TEST Loopback Adapter Installer
:: ========================================================
title AirBeam - Setup Offline Loopback Adapter
color 0b

echo ========================================================
echo   AirBeam Offline Hotspot Setup (Microsoft Loopback)
echo ========================================================
echo.
echo Installing Microsoft KM-TEST Loopback Adapter silently...

if exist "%~dp0InstallLoopback.exe" (
    "%~dp0InstallLoopback.exe"
) else if exist "%~dp0desktop-sender\InstallLoopback.exe" (
    "%~dp0desktop-sender\InstallLoopback.exe"
) else if exist "%~dp0assets\InstallLoopback.exe" (
    "%~dp0assets\InstallLoopback.exe"
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo Setup Complete! Loopback Adapter configured.
    echo ========================================================
) else (
    echo.
    echo Setup exited with code %ERRORLEVEL%. Please check %%TEMP%%\airbeam_loopback_install.log
)
echo.
pause
