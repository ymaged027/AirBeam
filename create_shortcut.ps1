$WshShell = New-Object -ComObject WScript.Shell

$Shortcut50 = $WshShell.CreateShortcut("C:\Users\youssef\Desktop\AirBeam v5.0.lnk")
$Shortcut50.TargetPath = "C:\Users\youssef\WirelessFileTransfer-v3.0\Launch-AirBeam-v5.0.bat"
$Shortcut50.WorkingDirectory = "C:\Users\youssef\WirelessFileTransfer-v3.0"
$Shortcut50.IconLocation = "C:\Users\youssef\WirelessFileTransfer-v3.0\desktop-sender\assets\airbeam.ico,0"
$Shortcut50.Description = "AirBeam v5.0 - PC to PC, Android and iPhone Ultra-Speed Wireless Transfer"
$Shortcut50.Save()
Write-Host "Desktop shortcut created successfully for AirBeam v5.0!"

$ShortcutMain = $WshShell.CreateShortcut("C:\Users\youssef\Desktop\AirBeam.lnk")
$ShortcutMain.TargetPath = "C:\Users\youssef\WirelessFileTransfer-v3.0\Launch-AirBeam.bat"
$ShortcutMain.WorkingDirectory = "C:\Users\youssef\WirelessFileTransfer-v3.0"
$ShortcutMain.IconLocation = "C:\Users\youssef\WirelessFileTransfer-v3.0\desktop-sender\assets\airbeam.ico,0"
$ShortcutMain.Description = "AirBeam - Ultra-Speed Wireless Transfer"
$ShortcutMain.Save()
Write-Host "Desktop shortcut created successfully for AirBeam.lnk!"

Get-ChildItem "C:\Users\youssef\Desktop\AirBeam*.lnk" | Where-Object { $_.Name -ne "AirBeam v5.0.lnk" -and $_.Name -ne "AirBeam.lnk" } | Remove-Item -Force
