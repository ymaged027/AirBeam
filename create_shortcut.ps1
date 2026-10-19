$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\youssef\Desktop\AirBeam v4.5.lnk")
$Shortcut.TargetPath = "C:\Users\youssef\WirelessFileTransfer-v3.0\Launch-AirBeam-v4.5.bat"
$Shortcut.WorkingDirectory = "C:\Users\youssef\WirelessFileTransfer-v3.0"
$Shortcut.IconLocation = "C:\Users\youssef\WirelessFileTransfer-v3.0\desktop-sender\assets\airbeam.ico,0"
$Shortcut.Description = "AirBeam v4.5 - PC to PC, Android and iPhone Ultra-Speed Wireless Transfer"
$Shortcut.Save()
Write-Host "Desktop shortcut created successfully for AirBeam v4.5!"

if (Test-Path "C:\Users\youssef\Desktop\AirBeam v4.4.lnk") {
    Remove-Item "C:\Users\youssef\Desktop\AirBeam v4.4.lnk" -Force
}
if (Test-Path "C:\Users\youssef\Desktop\AirBeam v4.3.lnk") {
    Remove-Item "C:\Users\youssef\Desktop\AirBeam v4.3.lnk" -Force
}
if (Test-Path "C:\Users\youssef\Desktop\AirBeam v4.2.lnk") {
    Remove-Item "C:\Users\youssef\Desktop\AirBeam v4.2.lnk" -Force
}
