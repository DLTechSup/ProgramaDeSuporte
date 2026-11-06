; Instalador do Demanda do Dia (Inno Setup 6). Instala só para o usuário atual,
; assim o programa pode gravar a lista e o login do WhatsApp sem pedir administrador.
[Setup]
AppName=Demanda do Dia
AppVersion=1.0.0
AppPublisher=DLTechSup
DefaultDirName={localappdata}\Programs\DemandaDoDia
DefaultGroupName=Demanda do Dia
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\saida
OutputBaseFilename=DemandaDoDia-Instalador
Compression=lzma2/fast
SolidCompression=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\assets\icone.ico
UninstallDisplayIcon={app}\DemandaWhatsApp.exe
WizardStyle=modern

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar um ícone na Área de Trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\dist\DemandaWhatsApp\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Demanda do Dia"; Filename: "{app}\DemandaWhatsApp.exe"
Name: "{autodesktop}\Demanda do Dia"; Filename: "{app}\DemandaWhatsApp.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DemandaWhatsApp.exe"; Description: "Abrir o Demanda do Dia"; Flags: nowait postinstall skipifsilent
