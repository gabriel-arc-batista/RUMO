[Setup]
AppId={{96028A65-51CB-4DA7-B623-512B6896BA09}
AppName=RUMO
AppVersion=1.4.1
AppPublisher=RUMO Local
SetupIconFile=..\assets\RUMO.ico
DefaultDirName={localappdata}\Programs\RUMO
DefaultGroupName=RUMO
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=RUMO-Instalar-Windows
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\RUMO.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "..\dist\RUMO\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CHECKLIST.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\FONTES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\RUMO"; Filename: "{app}\RUMO.exe"; IconFilename: "{app}\_internal\assets\RUMO.ico"
Name: "{autodesktop}\RUMO"; Filename: "{app}\RUMO.exe"; IconFilename: "{app}\_internal\assets\RUMO.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\RUMO.exe"; Description: "Abrir RUMO"; Flags: nowait postinstall skipifsilent
