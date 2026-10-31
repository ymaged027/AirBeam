@echo off
setlocal
cd /d "%~dp0"

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges to configure Windows Defender Firewall...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -Verb RunAs -ArgumentList '/c \"\"%~f0\"\" :ELEVATED'"
    exit /b
)

title AirBeam - Windows Defender Firewall Configurator

echo ======================================================================
echo    AirBeam High-Speed Transfer - Firewall Configuration
echo ======================================================================
echo.
echo Removing existing rules (if any)...
netsh advfirewall firewall delete rule name="AirBeam iOS Web Portal" >nul 2>&1
netsh advfirewall firewall delete rule name="AirBeam iOS Web Portal 8080" >nul 2>&1
netsh advfirewall firewall delete rule name="AirBeam High-Speed Transfer" >nul 2>&1
netsh advfirewall firewall delete rule name="AirBeam APK Server" >nul 2>&1
netsh advfirewall firewall delete rule name="AirBeam UDP Discovery" >nul 2>&1
netsh advfirewall firewall delete rule name="AirBeam mDNS Discovery" >nul 2>&1
netsh advfirewall firewall delete rule name="AirBeam Local DNS" >nul 2>&1
netsh advfirewall firewall delete rule name="AirBeam Pythonw Runtime" >nul 2>&1
netsh advfirewall firewall delete rule name="AirBeam Python Runtime" >nul 2>&1
netsh advfirewall firewall delete rule name="AirBeam Executable" >nul 2>&1
netsh advfirewall firewall delete rule name="AirBeam Installed App" >nul 2>&1

echo Adding inbound allow rules for all network profiles (Private, Public, Domain)...
netsh advfirewall firewall add rule name="AirBeam iOS Web Portal" dir=in action=allow protocol=TCP localport=8090 profile=any
netsh advfirewall firewall add rule name="AirBeam iOS Web Portal 8080" dir=in action=allow protocol=TCP localport=8080 profile=any
netsh advfirewall firewall add rule name="AirBeam High-Speed Transfer" dir=in action=allow protocol=TCP localport=7777 profile=any
netsh advfirewall firewall add rule name="AirBeam APK Server" dir=in action=allow protocol=TCP localport=8888 profile=any
netsh advfirewall firewall add rule name="AirBeam UDP Discovery" dir=in action=allow protocol=UDP localport=7778 profile=any
netsh advfirewall firewall add rule name="AirBeam mDNS Discovery" dir=in action=allow protocol=UDP localport=5353 profile=any
netsh advfirewall firewall add rule name="AirBeam Local DNS" dir=in action=allow protocol=UDP localport=53 profile=any

set "PYW=%LOCALAPPDATA%\Python\pythoncore-3.14-64\pythonw.exe"
if exist "%PYW%" (
    netsh advfirewall firewall add rule name="AirBeam Pythonw Runtime" dir=in action=allow program="%PYW%" profile=any
)
set "PY=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
if exist "%PY%" (
    netsh advfirewall firewall add rule name="AirBeam Python Runtime" dir=in action=allow program="%PY%" profile=any
)
if exist "%~dp0AirBeam.exe" (
    netsh advfirewall firewall add rule name="AirBeam Executable" dir=in action=allow program="%~dp0AirBeam.exe" profile=any
)
if exist "%LOCALAPPDATA%\Programs\AirBeam\AirBeam.exe" (
    netsh advfirewall firewall add rule name="AirBeam Installed App" dir=in action=allow program="%LOCALAPPDATA%\Programs\AirBeam\AirBeam.exe" profile=any
)

echo.
echo ======================================================================
echo   [SUCCESS] Windows Defender Firewall configured successfully!
echo   All AirBeam ports (8090, 8080, 7777, 8888, 7778, 5353, 53) and runtimes are allowed
echo   across all network adapters (Home Wi-Fi, Windows Hotspot, etc.)!
echo ======================================================================
echo.
echo Press any key to close this window...
pause >nul
exit /b 0
