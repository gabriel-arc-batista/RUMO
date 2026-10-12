[Setup]
AppId={{96028A65-51CB-4DA7-B623-512B6896BA09}
AppName=RUMO Estudos
AppVersion=2.0.0
AppPublisher=RUMO Estudos Local
SetupIconFile=..\assets\RUMO.ico
DefaultDirName={localappdata}\Programs\RUMO
UsePreviousAppDir=no
DefaultGroupName=RUMO Estudos
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
Name: "{group}\RUMO Estudos"; Filename: "{app}\RUMO.exe"; IconFilename: "{app}\_internal\assets\RUMO.ico"
Name: "{autodesktop}\RUMO Estudos"; Filename: "{app}\RUMO.exe"; IconFilename: "{app}\_internal\assets\RUMO.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\RUMO.exe"; Description: "Abrir RUMO Estudos"; Flags: nowait postinstall skipifsilent
