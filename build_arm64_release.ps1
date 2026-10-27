$ErrorActionPreference = "Stop"

$projectRoot = "C:\Users\youssef\WirelessFileTransfer-v3.0"
$distArm64 = "$projectRoot\dist\AirBeam-ARM64"
$runtimeDir = "$distArm64\runtime"
$setupOutputDir = "$projectRoot\setup-output"
$isccPath = "C:\Users\youssef\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
$cscPath = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"

Write-Host "=========================================================="
Write-Host " Building Native Windows ARM64 Release for AirBeam v6.0"
Write-Host "=========================================================="

if (-not (Test-Path $setupOutputDir)) {
    New-Item -ItemType Directory -Path $setupOutputDir -Force | Out-Null
}

# 1. Clean previous dist\AirBeam-ARM64 directory
if (Test-Path $distArm64) {
    Write-Host "Cleaning existing dist\AirBeam-ARM64..."
    Remove-Item $distArm64 -Recurse -Force
}
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

# 2. Obtain Python 3.12.8 ARM64 runtime
$zipArm64 = "$projectRoot\temp_arm64_check\python-3.12.8-arm64.zip"
if (-not (Test-Path $zipArm64)) {
    Write-Host "Downloading Python 3.12.8 ARM64 runtime..."
    $tempDir = "$projectRoot\temp_arm64_check"
    if (-not (Test-Path $tempDir)) { New-Item -ItemType Directory -Path $tempDir -Force | Out-Null }
    curl.exe -s -L -o $zipArm64 "https://www.python.org/ftp/python/3.12.8/python-3.12.8-arm64.zip"
}

Write-Host "Extracting Python 3.12.8 ARM64 runtime to $runtimeDir..."
Expand-Archive -Path $zipArm64 -DestinationPath $runtimeDir -Force

if (Test-Path "$runtimeDir\Doc") {
    Remove-Item "$runtimeDir\Doc" -Recurse -Force
}

# 3. Download and extract ARM64 wheels (pillow, qrcode, colorama)
Write-Host "Downloading ARM64 wheels for Python 3.12..."
$wheelDir = "$projectRoot\temp_arm64_wheels"
if (Test-Path $wheelDir) { Remove-Item $wheelDir -Recurse -Force }
New-Item -ItemType Directory -Path $wheelDir -Force | Out-Null

python -m pip download --platform win_arm64 --python-version 312 --only-binary=:all: -d $wheelDir pillow qrcode

$sitePackages = "$runtimeDir\Lib\site-packages"
if (-not (Test-Path $sitePackages)) {
    New-Item -ItemType Directory -Path $sitePackages -Force | Out-Null
}

Write-Host "Extracting wheels into $sitePackages..."
python -c "import zipfile, glob, os; [zipfile.ZipFile(f).extractall(r'$sitePackages') for f in glob.glob(r'$wheelDir\*.whl')]"
Remove-Item $wheelDir -Recurse -Force

# 4. Copy application source and assets
Write-Host "Copying desktop-sender into $distArm64..."
Copy-Item "$projectRoot\desktop-sender" "$distArm64\desktop-sender" -Recurse -Force

if (Test-Path "$projectRoot\release") {
    Write-Host "Copying release into $distArm64..."
    Copy-Item "$projectRoot\release" "$distArm64\release" -Recurse -Force
}

if (Test-Path "$projectRoot\Fix-AirBeam-Firewall.bat") {
    Copy-Item "$projectRoot\Fix-AirBeam-Firewall.bat" "$distArm64\Fix-AirBeam-Firewall.bat" -Force
}

if (Test-Path "$projectRoot\Fix-AirBeam-Loopback.bat") {
    Copy-Item "$projectRoot\Fix-AirBeam-Loopback.bat" "$distArm64\Fix-AirBeam-Loopback.bat" -Force
}

if (Test-Path "$projectRoot\InstallLoopback.exe") {
    Copy-Item "$projectRoot\InstallLoopback.exe" "$distArm64\InstallLoopback.exe" -Force
}

# Clean any cache or log files inside distArm64
Get-ChildItem -Path $distArm64 -Include "*.log", "last_home_wifi.txt", "airbeam_config.json", "iphone_hotspot_config.json", "__pycache__" -Recurse | Remove-Item -Recurse -Force

# 5. Compile AirBeam.exe launcher using csc.exe (/platform:anycpu)
Write-Host "Compiling AirBeamLauncher.cs to $distArm64\AirBeam.exe..."
& $cscPath /target:winexe /platform:anycpu /optimize+ /win32icon:"$projectRoot\desktop-sender\assets\airbeam.ico" /out:"$distArm64\AirBeam.exe" "$projectRoot\desktop-sender\AirBeamLauncher.cs"
if ($LASTEXITCODE -ne 0) {
    throw "AirBeam.exe compilation failed with exit code $LASTEXITCODE"
}

# 6. Build Portable ZIP (setup-output\AirBeam-v6.0-Windows-ARM64-Portable.zip)
$arm64Zip = "$setupOutputDir\AirBeam-v6.0-Windows-ARM64-Portable.zip"
if (Test-Path $arm64Zip) { Remove-Item $arm64Zip -Force }
Write-Host "Compressing $arm64Zip..."
Compress-Archive -Path "$distArm64\*" -DestinationPath $arm64Zip -CompressionLevel Optimal
Write-Host "ARM64 Portable ZIP created successfully!"

# 7. Compile Inno Setup Installer (setup-output\AirBeam-v5.6-Windows-ARM64-Setup.exe)
Write-Host "Compiling Inno Setup ARM64 installer..."
& $isccPath "$projectRoot\AirBeam-Setup-ARM64.iss"
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup ARM64 compilation failed with exit code $LASTEXITCODE"
}
Write-Host "ARM64 Setup Installer compiled successfully!"

# Cleanup temp files
if (Test-Path "$projectRoot\temp_arm64_check") {
    Remove-Item "$projectRoot\temp_arm64_check" -Recurse -Force
}

Write-Host "=========================================================="
Write-Host " Native Windows ARM64 Release Completed Successfully!"
Write-Host "=========================================================="
