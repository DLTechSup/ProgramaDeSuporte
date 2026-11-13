; Instalador do Renomeador em Massa (Inno Setup 6). Instala so para o usuario (nao pede administrador).
#define Nome "Renomeador em Massa"
#define Versao "1.0.0"
#define Exe "RenomeadorEmMassa.exe"

[Setup]
AppId={{B1D6E1B2-2C5E-4B4B-9A47-5E2A6A0F9C13}
AppName={#Nome}
AppVersion={#Versao}
AppPublisher=DLTechSup
DefaultDirName={autopf}\RenomeadorEmMassa
DefaultGroupName={#Nome}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\saida
OutputBaseFilename=RenomeadorEmMassa-Instalador-{#Versao}
SetupIconFile=..\assets\icone.ico
UninstallDisplayIcon={app}\{#Exe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "startup"; Description: "Iniciar junto com o Windows (fica na bandeja, perto do relógio)"; GroupDescription: "Opções:"
Name: "desktop"; Description: "Criar um atalho na Área de Trabalho"; GroupDescription: "Opções:"; Flags: unchecked

[Files]
Source: "..\dist\RenomeadorEmMassa\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#Nome}"; Filename: "{app}\{#Exe}"
Name: "{autodesktop}\{#Nome}"; Filename: "{app}\{#Exe}"; Tasks: desktop
Name: "{userstartup}\{#Nome}"; Filename: "{app}\{#Exe}"; Tasks: startup

[Run]
Filename: "{app}\{#Exe}"; Description: "Abrir o {#Nome} agora"; Flags: nowait postinstall skipifsilent
