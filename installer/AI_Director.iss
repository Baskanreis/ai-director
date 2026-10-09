#define MyAppName "AI Director"
#define MyAppVersion "2.101.7"
#define MyAppPublisher "AI Director"
#define MyAppExeName "AI_Director.exe"

[Setup]
AppId={{B9E2D4C1-8A47-4D6E-A1A7-0D6D4C8B2E17}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\AI Director
DefaultGroupName=AI Director
OutputDir=..\dist\installer
OutputBaseFilename=AI_Director_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\assets\AI_Director.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Uninstallable=yes
CreateUninstallRegKey=yes
DisableProgramGroupPage=yes

[Files]
Source: "..\dist\AI_Director\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AI Director"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\AI Director"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Ek kısayollar:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "AI Director'u başlat"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\models"
Type: filesandordirs; Name: "{app}\runtime"
