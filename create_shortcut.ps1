$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\youssef\Desktop\AirBeam v4.9.lnk")
$Shortcut.TargetPath = "C:\Users\youssef\WirelessFileTransfer-v3.0\Launch-AirBeam-v4.9.bat"
$Shortcut.WorkingDirectory = "C:\Users\youssef\WirelessFileTransfer-v3.0"
$Shortcut.IconLocation = "C:\Users\youssef\WirelessFileTransfer-v3.0\desktop-sender\assets\airbeam.ico,0"
$Shortcut.Description = "AirBeam v4.9 - PC to PC, Android and iPhone Ultra-Speed Wireless Transfer"
$Shortcut.Save()
Write-Host "Desktop shortcut created successfully for AirBeam v4.9!"

$Shortcut47 = $WshShell.CreateShortcut("C:\Users\youssef\Desktop\AirBeam v4.7.lnk")
$Shortcut47.TargetPath = "C:\Users\youssef\WirelessFileTransfer-v3.0\Launch-AirBeam-v4.7.bat"
$Shortcut47.WorkingDirectory = "C:\Users\youssef\WirelessFileTransfer-v3.0"
$Shortcut47.IconLocation = "C:\Users\youssef\WirelessFileTransfer-v3.0\desktop-sender\assets\airbeam.ico,0"
$Shortcut47.Description = "AirBeam v4.7/v4.9 - PC to PC, Android and iPhone Ultra-Speed Wireless Transfer"
$Shortcut47.Save()
Write-Host "Desktop shortcut created successfully for AirBeam v4.7!"

Get-ChildItem "C:\Users\youssef\Desktop\AirBeam*.lnk" | Where-Object { $_.Name -ne "AirBeam v4.9.lnk" -and $_.Name -ne "AirBeam v4.7.lnk" } | Remove-Item -Force
