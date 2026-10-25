$sourceDir = "C:\Users\youssef\WirelessFileTransfer-v3.0\dist\AirBeam"
$zipPath = "C:\Users\youssef\WirelessFileTransfer-v3.0\setup-output\AirBeam-v5.5-Portable.zip"

if (Test-Path "C:\Users\youssef\WirelessFileTransfer-v3.0\Fix-AirBeam-Firewall.bat") {
    Copy-Item "C:\Users\youssef\WirelessFileTransfer-v3.0\Fix-AirBeam-Firewall.bat" "$sourceDir\Fix-AirBeam-Firewall.bat" -Force
}

if (Test-Path "C:\Users\youssef\WirelessFileTransfer-v3.0\release") {
    Copy-Item "C:\Users\youssef\WirelessFileTransfer-v3.0\release" "$sourceDir\release" -Recurse -Force
}

# Clean any runtime state files from portable source directory
Get-ChildItem -Path "$sourceDir" -Include "airbeam_sender.log", "last_home_wifi.txt", "airbeam_config.json", "iphone_hotspot_config.json" -Recurse | Remove-Item -Force
if (Test-Path "$sourceDir\temp_staged_zips") {
    Remove-Item "$sourceDir\temp_staged_zips" -Recurse -Force
}

if (-not (Test-Path "C:\Users\youssef\WirelessFileTransfer-v3.0\setup-output")) {
    New-Item -ItemType Directory -Path "C:\Users\youssef\WirelessFileTransfer-v3.0\setup-output" -Force | Out-Null
}

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Write-Host "Creating portable ZIP archive from $sourceDir to $zipPath..."
Compress-Archive -Path "$sourceDir\*" -DestinationPath $zipPath -CompressionLevel Optimal
Write-Host "Portable ZIP created successfully at $zipPath!"
