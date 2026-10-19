; Script generated for Inno Setup 6
; AirBeam v5.0 Professional Setup Installer

#define MyAppName "AirBeam"
#define MyAppVersion "5.0"
#define MyAppPublisher "AirBeam Wireless"
#define MyAppExeName "AirBeam.exe"

[Setup]
AppId={{9B7E3E7A-624D-4F1A-98C3-B715C8F3A4B9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\AirBeam
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=C:\Users\youssef\WirelessFileTransfer-v3.0\setup-output
OutputBaseFilename=AirBeam-v5.0-Setup
SetupIconFile=C:\Users\youssef\WirelessFileTransfer-v3.0\desktop-sender\assets\airbeam.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "C:\Users\youssef\WirelessFileTransfer-v3.0\dist\AirBeam\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName} v{#MyAppVersion}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "netsh.exe"; Parameters: "advfirewall firewall add rule name=""AirBeam Transfer (TCP-In)"" dir=in action=allow protocol=TCP localport=8090,8080,7777,8888 profile=any"; Flags: runhidden; StatusMsg: "Configuring Windows Firewall for AirBeam ports..."
Filename: "netsh.exe"; Parameters: "advfirewall firewall add rule name=""AirBeam Discovery (UDP-In)"" dir=in action=allow protocol=UDP localport=7778 profile=any"; Flags: runhidden; StatusMsg: "Configuring Windows Firewall for AirBeam discovery..."
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName} v{#MyAppVersion}}"; Flags: nowait postinstall skipifsilent
