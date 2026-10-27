$WshShell = New-Object -ComObject WScript.Shell

$Shortcut60 = $WshShell.CreateShortcut("C:\Users\youssef\Desktop\AirBeam v6.0.lnk")
$Shortcut60.TargetPath = "C:\Users\youssef\WirelessFileTransfer-v3.0\AirBeam.exe"
$Shortcut60.WorkingDirectory = "C:\Users\youssef\WirelessFileTransfer-v3.0"
$Shortcut60.IconLocation = "C:\Users\youssef\WirelessFileTransfer-v3.0\AirBeam.exe,0"
$Shortcut60.Description = "AirBeam v6.0 - PC to PC, Android and iPhone Ultra-Speed Wireless Transfer"
$Shortcut60.Save()
Write-Host "Desktop shortcut created successfully for AirBeam v6.0!"

$ShortcutMain = $WshShell.CreateShortcut("C:\Users\youssef\Desktop\AirBeam.lnk")
$ShortcutMain.TargetPath = "C:\Users\youssef\WirelessFileTransfer-v3.0\AirBeam.exe"
$ShortcutMain.WorkingDirectory = "C:\Users\youssef\WirelessFileTransfer-v3.0"
$ShortcutMain.IconLocation = "C:\Users\youssef\WirelessFileTransfer-v3.0\AirBeam.exe,0"
$ShortcutMain.Description = "AirBeam - Ultra-Speed Wireless Transfer"
$ShortcutMain.Save()
Write-Host "Desktop shortcut created successfully for AirBeam.lnk!"

Get-ChildItem "C:\Users\youssef\Desktop\AirBeam*.lnk" | Where-Object { $_.Name -ne "AirBeam v6.0.lnk" -and $_.Name -ne "AirBeam.lnk" } | Remove-Item -Force

