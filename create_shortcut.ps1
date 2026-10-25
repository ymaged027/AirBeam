$WshShell = New-Object -ComObject WScript.Shell

$Shortcut56 = $WshShell.CreateShortcut("C:\Users\youssef\Desktop\AirBeam v5.6.lnk")
$Shortcut56.TargetPath = "C:\Users\youssef\WirelessFileTransfer-v3.0\AirBeam.exe"
$Shortcut56.WorkingDirectory = "C:\Users\youssef\WirelessFileTransfer-v3.0"
$Shortcut56.IconLocation = "C:\Users\youssef\WirelessFileTransfer-v3.0\AirBeam.exe,0"
$Shortcut56.Description = "AirBeam v5.6 - PC to PC, Android and iPhone Ultra-Speed Wireless Transfer"
$Shortcut56.Save()
Write-Host "Desktop shortcut created successfully for AirBeam v5.6!"

$ShortcutMain = $WshShell.CreateShortcut("C:\Users\youssef\Desktop\AirBeam.lnk")
$ShortcutMain.TargetPath = "C:\Users\youssef\WirelessFileTransfer-v3.0\AirBeam.exe"
$ShortcutMain.WorkingDirectory = "C:\Users\youssef\WirelessFileTransfer-v3.0"
$ShortcutMain.IconLocation = "C:\Users\youssef\WirelessFileTransfer-v3.0\AirBeam.exe,0"
$ShortcutMain.Description = "AirBeam - Ultra-Speed Wireless Transfer"
$ShortcutMain.Save()
Write-Host "Desktop shortcut created successfully for AirBeam.lnk!"

Get-ChildItem "C:\Users\youssef\Desktop\AirBeam*.lnk" | Where-Object { $_.Name -ne "AirBeam v5.6.lnk" -and $_.Name -ne "AirBeam.lnk" } | Remove-Item -Force

