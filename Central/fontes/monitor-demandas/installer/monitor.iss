; Instalador do Monitor de Demandas (Inno Setup 6). Instala so para o usuario (nao pede senha de administrador).
#define Nome "Monitor de Demandas"
#define Versao "1.0.0"
#define Exe "MonitorDeDemandas.exe"

[Setup]
AppId={{7A3C5C0E-6D1B-4C86-9E0B-3B1F4A9C2D71}
AppName={#Nome}
AppVersion={#Versao}
AppPublisher=DLTechSup
DefaultDirName={autopf}\MonitorDeDemandas
DefaultGroupName={#Nome}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\saida
OutputBaseFilename=MonitorDeDemandas-Instalador-{#Versao}
SetupIconFile=..\assets\icone.ico
UninstallDisplayIcon={app}\{#Exe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktop"; Description: "Criar um atalho na Área de Trabalho"; GroupDescription: "Atalhos:"
Name: "startup"; Description: "Iniciar junto com o Windows (fica na bandeja, perto do relógio)"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "..\dist\MonitorDeDemandas\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#Nome}"; Filename: "{app}\{#Exe}"
Name: "{autodesktop}\{#Nome}"; Filename: "{app}\{#Exe}"; Tasks: desktop
Name: "{userstartup}\{#Nome}"; Filename: "{app}\{#Exe}"; Tasks: startup

[Run]
Filename: "{app}\{#Exe}"; Description: "Abrir o {#Nome} agora"; Flags: nowait postinstall skipifsilent
