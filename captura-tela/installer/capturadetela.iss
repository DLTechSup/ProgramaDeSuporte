; Instalador do Captura de Tela (Inno Setup 6). Instala so para o usuario (nao pede administrador).
#define Nome "Captura de Tela"
#define Versao "1.0.0"
#define Exe "CapturaDeTela.exe"

[Setup]
AppId={{4C9E1A77-8F2B-4D5C-9A61-2E7B9F0C3A55}
AppName={#Nome}
AppVersion={#Versao}
AppPublisher=DLTechSup
DefaultDirName={autopf}\CapturaDeTela
DefaultGroupName={#Nome}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\saida
OutputBaseFilename=CapturaDeTela-Instalador-{#Versao}
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
Name: "startup"; Description: "Iniciar junto com o Windows (fica na bandeja, perto do relógio)"
Name: "desktop"; Description: "Criar um atalho na Área de Trabalho"; GroupDescription: "Opções:"; Flags: unchecked

[Files]
Source: "..\dist\CapturaDeTela\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#Nome}"; Filename: "{app}\{#Exe}"
Name: "{autodesktop}\{#Nome}"; Filename: "{app}\{#Exe}"; Tasks: desktop
Name: "{userstartup}\{#Nome}"; Filename: "{app}\{#Exe}"; Tasks: startup

[Run]
Filename: "{app}\{#Exe}"; Description: "Abrir o {#Nome} agora"; Flags: nowait postinstall skipifsilent
