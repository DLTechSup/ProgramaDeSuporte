// Funcoes que REMOVEM / reiniciam / imprimem teste. Cada acao grava no log.
const { acaoPS, executar, sys32, q } = require('./powershell.cjs');
const consultas = require('./consultas.cjs');
const backup = require('./backup.cjs');
const log = require('./log.cjs');

function resultado(etapa, comando, item, r, okExtra) {
  const ok = r.ok || (okExtra && okExtra(r));
  log.registrar({ etapa, comando, item, resultado: ok ? 'OK' : 'FALHA', msg: ok ? r.msg || '' : r.msg || `codigo ${r.code}` });
  return { ok, msg: r.msg || '' };
}

// Etapa 2
async function removerFila(nome) {
  const r = await acaoPS(`Remove-Printer -Name ${q(nome)}`);
  return resultado(2, `Remove-Printer -Name '${nome}'`, nome, r);
}

// Etapa 3 - sucesso se returncode == 0 (3010 = ok, pede reinicio)
async function removerFantasma(instanceId) {
  const r = await executar(sys32('pnputil.exe'), ['/remove-device', instanceId], { oem: true });
  const out = { ok: r.code === 0 || r.code === 3010, code: r.code, msg: (r.stderr || r.stdout).trim().slice(-300) };
  return resultado(3, `pnputil /remove-device "${instanceId}"`, instanceId, out);
}

// Etapa 4 - tenta com -RemoveFromDriverStore e, se falhar, sem ele
async function removerDriverSpooler(nome) {
  let r = await acaoPS(`Remove-PrinterDriver -Name ${q(nome)} -RemoveFromDriverStore`);
  if (r.ok) return resultado(4, `Remove-PrinterDriver -Name '${nome}' -RemoveFromDriverStore`, nome, r);
  log.registrar({ etapa: 4, comando: 'Remove-PrinterDriver -RemoveFromDriverStore', item: nome, resultado: 'AVISO', msg: `${r.msg} - tentando sem -RemoveFromDriverStore` });
  r = await acaoPS(`Remove-PrinterDriver -Name ${q(nome)}`);
  return resultado(4, `Remove-PrinterDriver -Name '${nome}'`, nome, r);
}

// Etapa 5 - backup primeiro, depois pnputil /delete-driver
async function removerPacote(oem, pastaBackup) {
  if (pastaBackup) {
    const b = await backup.exportar(pastaBackup, oem);
    log.registrar({ etapa: 5, comando: `pnputil /export-driver ${oem}`, item: oem, resultado: b.ok ? 'OK' : 'FALHA', msg: b.ok ? b.destino : b.msg });
    if (!b.ok) return { ok: false, msg: 'Backup falhou - pacote preservado. ' + b.msg };
  }
  const r = await executar(sys32('pnputil.exe'), ['/delete-driver', oem, '/uninstall', '/force'], { oem: true });
  const out = { ok: r.code === 0 || r.code === 3010, code: r.code, msg: (r.stderr || r.stdout).trim().slice(-300) };
  const res = resultado(5, `pnputil /delete-driver ${oem} /uninstall /force`, oem, out);
  if (!res.ok) log.registrar({ etapa: 5, item: oem, resultado: 'AVISO', msg: 'O pacote pode estar em uso' });
  return res;
}

async function reiniciarSpooler() {
  const r = await acaoPS('Restart-Service -Name Spooler -Force');
  return resultado(6, 'Restart-Service -Name Spooler -Force', 'Spooler', r);
}

async function reiniciarComputador() {
  const r = await executar(sys32('shutdown.exe'), ['/r', '/t', '5'], { oem: true });
  const out = { ok: r.code === 0, code: r.code, msg: (r.stderr || r.stdout).trim() };
  return resultado(6, 'shutdown /r /t 5', 'Computador', out);
}

async function pontoRestauracao() {
  const r = await acaoPS('Checkpoint-Computer -Description "LimpadorUSB" -RestorePointType MODIFY_SETTINGS');
  if (!r.ok) {
    log.registrar({ etapa: 0, comando: 'Checkpoint-Computer', item: 'Ponto de restauracao', resultado: 'AVISO', msg: (r.msg || 'nao foi possivel criar') + ' - seguindo sem ponto de restauracao' });
    return { ok: false, msg: r.msg };
  }
  log.registrar({ etapa: 0, comando: 'Checkpoint-Computer', item: 'Ponto de restauracao', resultado: 'OK' });
  return { ok: true, msg: '' };
}

async function paginaTeste(nome) {
  const filtro = `Name='${String(nome).replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`;
  const r = await acaoPS(
    `Invoke-CimMethod -InputObject (Get-CimInstance Win32_Printer -Filter ${q(filtro)}) -MethodName PrintTestPage | Out-Null`
  );
  return resultado('F', 'PrintTestPage', nome, r);
}

async function encerrarProcessos(ids) {
  let ok = 0;
  let falhas = 0;
  for (const p of ids) {
    const r = await acaoPS(`Stop-Process -Id ${parseInt(p.id, 10)} -Force`);
    const res = resultado('F', `Stop-Process -Id ${p.id}`, p.nome || String(p.id), r);
    res.ok ? ok++ : falhas++;
  }
  return { ok, falhas };
}

const CHAVE_BUSCA = 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\DriverSearching';
const CHAVE_META = 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Device Metadata';

async function lerBloqueio() {
  const lista = await require('./powershell.cjs').executarPS(
    `$a = (Get-ItemProperty ${q(CHAVE_BUSCA)} -ErrorAction SilentlyContinue).SearchOrderConfig; ` +
      `$b = (Get-ItemProperty ${q(CHAVE_META)} -ErrorAction SilentlyContinue).PreventDeviceMetadataFromNetwork; ` +
      '[pscustomobject]@{ SearchOrderConfig = $a; PreventDeviceMetadataFromNetwork = $b }'
  );
  const v = lista[0] || {};
  return { ligado: v.SearchOrderConfig === 0 && v.PreventDeviceMetadataFromNetwork === 1, ...v };
}

// ligar: SearchOrderConfig=0 e PreventDeviceMetadataFromNetwork=1 | desligar: 1 e 0
async function definirBloqueio(ligar) {
  const busca = ligar ? 0 : 1;
  const meta = ligar ? 1 : 0;
  const r = await acaoPS(
    `New-Item -Path ${q(CHAVE_BUSCA)} -Force | Out-Null; New-Item -Path ${q(CHAVE_META)} -Force | Out-Null; ` +
      `New-ItemProperty -Path ${q(CHAVE_BUSCA)} -Name SearchOrderConfig -Value ${busca} -PropertyType DWord -Force | Out-Null; ` +
      `New-ItemProperty -Path ${q(CHAVE_META)} -Name PreventDeviceMetadataFromNetwork -Value ${meta} -PropertyType DWord -Force | Out-Null`
  );
  return resultado('F', `Bloqueio de instalacao automatica = ${ligar ? 'ligado' : 'desligado'}`, 'Registro', r);
}

async function restaurarBackup(pasta) {
  const r = await backup.restaurar(pasta);
  return resultado('F', `pnputil /add-driver "${pasta}\\*.inf" /subdirs /install`, pasta, r);
}

async function abrirAtalho(tipo) {
  const mapa = {
    devmgmt: ['devmgmt.msc'],
    impressoras: ['control.exe', 'printers'],
    printmanagement: ['printmanagement.msc'],
    servicos: ['services.msc']
  };
  const cmd = mapa[tipo];
  if (!cmd) return { ok: false, msg: 'Atalho desconhecido' };
  // "cmd /c start" abre msc/control sem janela de console
  const r = await executar(sys32('cmd.exe'), ['/c', 'start', '""', ...cmd], { timeout: 10000 });
  return { ok: r.code === 0, msg: r.code === 0 ? '' : 'Nao foi possivel abrir (pode nao existir neste Windows).' };
}

module.exports = {
  removerFila,
  removerFantasma,
  removerDriverSpooler,
  removerPacote,
  reiniciarSpooler,
  reiniciarComputador,
  pontoRestauracao,
  paginaTeste,
  encerrarProcessos,
  lerBloqueio,
  definirBloqueio,
  restaurarBackup,
  abrirAtalho,
  listarProcessos: consultas.processos
};
