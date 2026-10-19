$sourceDir = "C:\Users\youssef\WirelessFileTransfer-v3.0\dist\AirBeam"
$zipPath = "C:\Users\youssef\WirelessFileTransfer-v3.0\setup-output\AirBeam-v4.8-Portable.zip"

if (-not (Test-Path "C:\Users\youssef\WirelessFileTransfer-v3.0\setup-output")) {
    New-Item -ItemType Directory -Path "C:\Users\youssef\WirelessFileTransfer-v3.0\setup-output" -Force | Out-Null
}

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Write-Host "Creating portable ZIP archive from $sourceDir to $zipPath..."
Compress-Archive -Path "$sourceDir\*" -DestinationPath $zipPath -CompressionLevel Optimal
Write-Host "Portable ZIP created successfully at $zipPath!"
