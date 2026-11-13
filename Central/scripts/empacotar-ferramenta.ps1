# Compila UMA ferramenta (Python/PyInstaller ou Electron) e deixa o resultado em <Saida>\<Id>.
# Usado pela compilação da Central (.github/workflows/build-central.yml). Roda no Windows.
param([Parameter(Mandatory = $true)][string]$Id, [Parameter(Mandatory = $true)][string]$Saida)
$ErrorActionPreference = 'Stop'
$src = Join-Path $PSScriptRoot "..\fontes\$Id" | Resolve-Path
$out = Join-Path $Saida $Id
New-Item -ItemType Directory -Force $out | Out-Null
Push-Location $src
function Sh([scriptblock]$b) { & $b; if ($LASTEXITCODE -ne 0) { throw "comando falhou ($LASTEXITCODE)" } }
try {
  switch ($Id) {
    'nomes-calcados' {
      Sh { pip install -r requirements.txt pyinstaller }
      Sh { pyinstaller --noconfirm --onefile --noconsole --name NomesCalcados --collect-all customtkinter --collect-all ddgs --collect-all primp --collect-all selectolax --collect-all rapidfuzz --collect-all freelm --collect-all tkinterdnd2 programa.py }
      Copy-Item dist\NomesCalcados.exe $out
      Copy-Item -Recurse config, regras, dados $out
      Remove-Item "$out\dados\*.db" -ErrorAction SilentlyContinue
      Copy-Item .env.exemplo, LEIA-ME.md $out
      New-Item -ItemType Directory "$out\logs" -Force | Out-Null
    }
    'monitor-demandas' {
      Sh { pip install -r requirements.txt pyinstaller }
      Sh { pyinstaller --noconfirm --onedir --noconsole --name MonitorDeDemandas --icon assets/icone.ico --version-file installer/versao.txt --add-data "assets;assets" --collect-all playwright --collect-all customtkinter --collect-all pystray --collect-all rapidocr_onnxruntime --collect-all onnxruntime --collect-all rapidfuzz programa.py }
      Copy-Item -Recurse dist\MonitorDeDemandas\* $out
    }
    'renomeador' {
      Sh { pip install -r requirements.txt pyinstaller }
      Sh { pyinstaller --noconfirm --onedir --noconsole --name RenomeadorEmMassa --icon assets/icone.ico --version-file installer/versao.txt --add-data "assets;assets" --collect-all customtkinter --collect-all pystray programa.py }
      Copy-Item -Recurse dist\RenomeadorEmMassa\* $out
    }
    'captura-tela' {
      Sh { pip install -r requirements.txt pyinstaller }
      Sh { pyinstaller --noconfirm --onedir --noconsole --name CapturaDeTela --icon assets/icone.ico --version-file installer/versao.txt --add-data "assets;assets" --collect-all customtkinter --collect-all pystray --collect-all pynput --hidden-import win32clipboard --hidden-import win32con --hidden-import win32timezone programa.py }
      Copy-Item -Recurse dist\CapturaDeTela\* $out
    }
    'executar-py' {
      # precisa ser instalado (associa o .py), então vai o instalador do próprio programa
      Sh { pip install -r requirements.txt pyinstaller }
      Sh { pyinstaller --noconfirm --onedir --console --name ExecutarPy --icon assets/icone.ico --version-file installer/versao.txt programa.py }
      Sh { choco install innosetup --no-progress -y }
      Sh { & "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" installer\executarpy.iss }
      Copy-Item saida\ExecutarPy-Instalador-*.exe $out
    }
    'separador-fotos' {
      Sh { pip install -r requirements.txt pyinstaller }
      Sh { pyinstaller --noconfirm --onefile --noconsole --name SeparadorFotos --collect-all rapidocr_onnxruntime --collect-all onnxruntime separador.py }
      Copy-Item dist\SeparadorFotos.exe $out
      Copy-Item marcas.txt, LEIAME.md $out
    }
    'editor-fotos' {
      Sh { npm ci }
      Sh { npm run build }
      Sh { npx electron-builder --win portable --x64 --publish never }
      Copy-Item dist\*.exe $out
    }
    'limpador-usb' {
      Sh { npm ci }
      Sh { npx vite build }
      Sh { npx electron-builder --win portable --x64 --publish never }
      Copy-Item release\*.exe $out
    }
    default { throw "ferramenta desconhecida: $Id" }
  }
  Get-ChildItem $out -Recurse -File | Measure-Object Length -Sum | ForEach-Object { "{0}: {1} arquivo(s), {2:N1} MB" -f $Id, $_.Count, ($_.Sum / 1MB) }
} finally { Pop-Location }
