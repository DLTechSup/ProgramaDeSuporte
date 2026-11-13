; Instalador do Executar .py (Inno Setup 6). Instala so para o usuario (nao pede administrador).
; Associa .py a ExecutarPy.exe, guardando a associacao anterior para poder desfazer (manual ou ao desinstalar).
#define Nome "Executar .py"
#define Versao "1.0.0"
#define Exe "ExecutarPy.exe"

[Setup]
AppId={{9F3A7C2E-4B8D-4E11-9C6A-7D2E5F1A80B6}
AppName={#Nome}
AppVersion={#Versao}
AppPublisher=DLTechSup
DefaultDirName={autopf}\ExecutarPy
DefaultGroupName={#Nome}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\saida
OutputBaseFilename=ExecutarPy-Instalador-{#Versao}
SetupIconFile=..\assets\icone.ico
UninstallDisplayIcon={app}\{#Exe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "associar"; Description: "Associar arquivos .py a este programa (abrir com duplo clique)"
Name: "desktop"; Description: "Criar um atalho na Área de Trabalho"; GroupDescription: "Opções:"; Flags: unchecked

[Files]
Source: "..\dist\ExecutarPy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "DesfazerAssociacao.cmd"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#Nome}"; Filename: "{app}\{#Exe}"
Name: "{autoprograms}\Desfazer associação com .py"; Filename: "{app}\DesfazerAssociacao.cmd"
Name: "{autodesktop}\{#Nome}"; Filename: "{app}\{#Exe}"; Tasks: desktop

[Code]
procedure SalvarBackupEAssociar();
var
  valorAntigo: String;
  app: String;
begin
  app := ExpandConstant('{app}');
  if not RegQueryStringValue(HKCU, 'Software\Classes\.py', '', valorAntigo) then
    valorAntigo := 'NAO_HAVIA';
  SaveStringToFile(app + '\backup_associacao.txt', valorAntigo, False);

  RegWriteStringValue(HKCU, 'Software\Classes\ExecutarPy.py', '', 'Script Python (Executar .py)');
  RegWriteStringValue(HKCU, 'Software\Classes\ExecutarPy.py\DefaultIcon', '', app + '\{#Exe},0');
  RegWriteStringValue(HKCU, 'Software\Classes\ExecutarPy.py\shell\open\command', '', '"' + app + '\{#Exe}" "%1" %*');
  RegWriteStringValue(HKCU, 'Software\Classes\.py', '', 'ExecutarPy.py');
end;

procedure RestaurarAssociacao();
var
  bruto: AnsiString;
  valorAntigo: String;
  app: String;
begin
  app := ExpandConstant('{app}');
  if LoadStringFromFile(app + '\backup_associacao.txt', bruto) then
  begin
    valorAntigo := Trim(String(bruto));
    if valorAntigo = 'NAO_HAVIA' then
      RegDeleteValue(HKCU, 'Software\Classes\.py', '')
    else
      RegWriteStringValue(HKCU, 'Software\Classes\.py', '', valorAntigo);
  end;
  RegDeleteKeyIncludingSubkeys(HKCU, 'Software\Classes\ExecutarPy.py');
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and IsTaskSelected('associar') then
    SalvarBackupEAssociar();
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RestaurarAssociacao();
end;

[Run]
Filename: "{app}\DesfazerAssociacao.cmd"; Description: "Não quero esta associação; desfazer agora"; Flags: postinstall skipifsilent unchecked
