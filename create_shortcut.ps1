$WshShell = New-Object -ComObject WScript.Shell

$Shortcut57 = $WshShell.CreateShortcut("C:\Users\youssef\Desktop\AirBeam v5.7.lnk")
$Shortcut57.TargetPath = "C:\Users\youssef\WirelessFileTransfer-v3.0\AirBeam.exe"
$Shortcut57.WorkingDirectory = "C:\Users\youssef\WirelessFileTransfer-v3.0"
$Shortcut57.IconLocation = "C:\Users\youssef\WirelessFileTransfer-v3.0\AirBeam.exe,0"
$Shortcut57.Description = "AirBeam v5.7 - PC to PC, Android and iPhone Ultra-Speed Wireless Transfer"
$Shortcut57.Save()
Write-Host "Desktop shortcut created successfully for AirBeam v5.7!"

$ShortcutMain = $WshShell.CreateShortcut("C:\Users\youssef\Desktop\AirBeam.lnk")
$ShortcutMain.TargetPath = "C:\Users\youssef\WirelessFileTransfer-v3.0\AirBeam.exe"
$ShortcutMain.WorkingDirectory = "C:\Users\youssef\WirelessFileTransfer-v3.0"
$ShortcutMain.IconLocation = "C:\Users\youssef\WirelessFileTransfer-v3.0\AirBeam.exe,0"
$ShortcutMain.Description = "AirBeam - Ultra-Speed Wireless Transfer"
$ShortcutMain.Save()
Write-Host "Desktop shortcut created successfully for AirBeam.lnk!"

Get-ChildItem "C:\Users\youssef\Desktop\AirBeam*.lnk" | Where-Object { $_.Name -ne "AirBeam v5.7.lnk" -and $_.Name -ne "AirBeam.lnk" } | Remove-Item -Force

