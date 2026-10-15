// Funcoes que LISTAM. As regras seguem fielmente o LiberarPortasUSB.bat.
const { executarPS, executar, sys32 } = require('./powershell.cjs');

// Etapa 2 - filas de impressao em portas USB
function filas() {
  return executarPS(
    "Get-Printer | Where-Object { $_.PortName -like 'USB*' } | " +
      "Select-Object Name, PortName, DriverName, @{n='PrinterStatus';e={[string]$_.PrinterStatus}}"
  );
}

// Etapa 3 - dispositivos fantasma (mesmo filtro do script)
function fantasmas() {
  return executarPS(
    'Get-PnpDevice | Where-Object { (-not $_.Present) -and ( ' +
      "$_.Class -in @('Printer','PrintQueue') -or " +
      "$_.InstanceId -like 'USBPRINT\\*' -or " +
      "$_.Service -eq 'usbprint' ) } | " +
      'Select-Object FriendlyName, Class, InstanceId'
  );
}

// Etapa 4 - drivers do Spooler que nao estao em uso
function driversSpooler() {
  return executarPS(
    '$emUso = @(Get-Printer | ForEach-Object { $_.DriverName }); ' +
      'Get-PrinterDriver | Where-Object { ' +
      "$_.Manufacturer -notmatch 'Microsoft' -and " +
      "$_.Name -notmatch 'Microsoft|OneNote|Fax|XPS|PDF' -and " +
      '$emUso -notcontains $_.Name } | Select-Object Name, Manufacturer'
  );
}

// Fallback da etapa 5: le o "pnputil /enum-drivers" aceitando PT e EN.
function interpretarPnputil(texto) {
  const blocos = texto.split(/\r?\n\s*\r?\n/);
  const saida = [];
  for (const bloco of blocos) {
    const reg = {};
    for (const linha of bloco.split(/\r?\n/)) {
      const i = linha.indexOf(':');
      if (i < 0) continue;
      const chave = linha.slice(0, i).trim().toLowerCase();
      const valor = linha.slice(i + 1).trim();
      if (!reg.Driver && /^(nome publicado|published name)/.test(chave)) reg.Driver = valor;
      else if (!reg.OriginalFileName && /original/.test(chave)) reg.OriginalFileName = valor;
      else if (!reg.ProviderName && /(provedor|provider)/.test(chave)) reg.ProviderName = valor;
      else if (!reg.ClassName && /^(nome da classe|class name|classe)/.test(chave) && !/guid/.test(chave))
        reg.ClassName = valor;
      else if (!reg.Version && /(vers|date|data)/.test(chave)) reg.Version = valor;
    }
    if (reg.Driver && /printer|impressora/i.test(reg.ClassName || '') && !/microsoft/i.test(reg.ProviderName || '')) {
      saida.push({
        Driver: reg.Driver,
        ProviderName: reg.ProviderName || '',
        OriginalFileName: reg.OriginalFileName || '',
        Version: reg.Version || ''
      });
    }
  }
  return saida;
}

// Etapa 5 - pacotes de driver (oemXX.inf)
async function pacotes() {
  try {
    return await executarPS(
      'Get-WindowsDriver -Online | Where-Object { $_.ClassName -eq ' +
        "'Printer' -and $_.ProviderName -notmatch 'Microsoft' } | " +
        "Select-Object Driver, ProviderName, OriginalFileName, @{n='Version';e={[string]$_.Version}}",
      { timeout: 120000 }
    );
  } catch (e) {
    const r = await executar(sys32('pnputil.exe'), ['/enum-drivers'], { oem: true, timeout: 120000 });
    if (r.code !== 0) throw e;
    return interpretarPnputil(r.stdout);
  }
}

function portasVirtuais() {
  return executarPS("Get-PrinterPort | Where-Object { $_.Name -like 'USB*' } | Select-Object Name, Description");
}

// Impressora USB conectada agora
function conectadas() {
  return executarPS(
    'Get-PnpDevice -PresentOnly | Where-Object { ' +
      "$_.InstanceId -like 'USBPRINT\\*' -or $_.Service -eq 'usbprint' } | " +
      'Select-Object FriendlyName, InstanceId'
  );
}

// Todas as impressoras instaladas (para a pagina de teste)
function impressoras() {
  return executarPS(
    "Get-Printer | Select-Object Name, PortName, DriverName, @{n='PrinterStatus';e={[string]$_.PrinterStatus}}"
  );
}

async function suporteRemoveDevice() {
  const r = await executar(sys32('pnputil.exe'), ['/?'], { oem: true, timeout: 15000 });
  return /remove-device/i.test(r.stdout + r.stderr);
}

// Painel inicial: roda tudo em paralelo; uma falha nao derruba as demais.
async function painel() {
  const nomes = ['filas', 'fantasmas', 'drivers', 'pacotes', 'portas', 'conectadas'];
  const res = await Promise.allSettled([filas(), fantasmas(), driversSpooler(), pacotes(), portasVirtuais(), conectadas()]);
  const out = { erros: {} };
  res.forEach((r, i) => {
    out[nomes[i]] = r.status === 'fulfilled' ? r.value : [];
    if (r.status === 'rejected') out.erros[nomes[i]] = String(r.reason && r.reason.message ? r.reason.message : r.reason);
  });
  // Junta portas virtuais com as filas que as usam.
  const mapa = new Map();
  for (const p of out.portas) mapa.set(String(p.Name).toUpperCase(), { porta: p.Name, impressora: null, status: 'Livre' });
  for (const f of out.filas) {
    const chave = String(f.PortName).toUpperCase();
    const atual = mapa.get(chave) || { porta: f.PortName };
    mapa.set(chave, { porta: f.PortName, impressora: f.Name, status: f.PrinterStatus || 'Em uso' });
  }
  out.tabelaPortas = [...mapa.values()].sort((a, b) => a.porta.localeCompare(b.porta, undefined, { numeric: true }));
  out.removeDevice = await suporteRemoveDevice();
  return out;
}

// Processos que podem segurar a porta (Status Monitor etc.)
async function processos() {
  const lista = await executarPS(
    'Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -or $_.Company } | ' +
      'Select-Object Name, Id, Path, Company'
  );
  const marca = /(^|[^a-z])(epson|canon|hp|hewlett|brother)([^a-z]|$)/i;
  return lista.filter((p) => marca.test(`${p.Company || ''} ${p.Path || ''} ${p.Name || ''}`));
}

module.exports = {
  filas,
  fantasmas,
  driversSpooler,
  pacotes,
  portasVirtuais,
  conectadas,
  impressoras,
  processos,
  painel,
  suporteRemoveDevice,
  interpretarPnputil
};
