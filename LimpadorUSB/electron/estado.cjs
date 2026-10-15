// Progresso da limpeza (estado.json), configuracao e tarefa agendada de retomada.
const fs = require('fs');
const path = require('path');
const { BASE, ESTADO, CONFIG } = require('./caminhos.cjs');
const { executar, sys32 } = require('./powershell.cjs');
const log = require('./log.cjs');

const TAREFA = 'LimpadorUSB_Retomar';

function garantirPasta() {
  fs.mkdirSync(BASE, { recursive: true });
}

// Escreve em arquivo temporario e renomeia, para nao corromper.
function gravarAtomico(destino, obj) {
  garantirPasta();
  const tmp = destino + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(obj, null, 2), 'utf8');
  fs.renameSync(tmp, destino);
}

function lerJson(arquivo) {
  try {
    return JSON.parse(fs.readFileSync(arquivo, 'utf8').replace(/^\uFEFF/, ''));
  } catch (_) {
    return null;
  }
}

function carregar() {
  const e = lerJson(ESTADO);
  return e && e.versao === 1 ? e : null;
}

function salvar(estado) {
  gravarAtomico(ESTADO, { versao: 1, ...estado });
  return true;
}

function limpar() {
  try {
    fs.rmSync(ESTADO, { force: true });
  } catch (_) {
    /* ignora */
  }
  return true;
}

function carregarConfig() {
  return lerJson(CONFIG) || {};
}

function salvarConfig(parcial) {
  const nova = { ...carregarConfig(), ...parcial };
  gravarAtomico(CONFIG, nova);
  return nova;
}

// Caminho do executavel. No modo "portable" o exe roda de uma pasta temporaria,
// entao o caminho real do arquivo vem de PORTABLE_EXECUTABLE_FILE.
function caminhoExe() {
  return process.env.PORTABLE_EXECUTABLE_FILE || process.execPath;
}

async function agendarRetomada() {
  if (process.platform !== 'win32') return { ok: false, msg: 'Somente no Windows' };
  const exe = caminhoExe();
  const r = await executar(
    sys32('schtasks.exe'),
    ['/Create', '/TN', TAREFA, '/TR', `"${exe}" --retomar`, '/SC', 'ONLOGON', '/RL', 'HIGHEST', '/F'],
    { oem: true }
  );
  log.registrar({
    comando: 'schtasks /Create ' + TAREFA,
    resultado: r.code === 0 ? 'OK' : 'FALHA',
    msg: r.code === 0 ? 'Retomada automatica agendada' : (r.stderr || r.stdout).trim()
  });
  return { ok: r.code === 0, msg: (r.stderr || '').trim() };
}

async function removerRetomada() {
  if (process.platform !== 'win32') return { ok: true };
  const r = await executar(sys32('schtasks.exe'), ['/Delete', '/TN', TAREFA, '/F'], { oem: true });
  log.registrar({
    comando: 'schtasks /Delete ' + TAREFA,
    resultado: r.code === 0 ? 'OK' : 'INFO',
    msg: r.code === 0 ? 'Tarefa de retomada removida' : 'Tarefa nao existia'
  });
  return { ok: r.code === 0 };
}

// Encerra de vez: apaga estado.json e a tarefa agendada.
async function encerrar() {
  limpar();
  await removerRetomada();
  return true;
}

module.exports = {
  TAREFA,
  carregar,
  salvar,
  limpar,
  carregarConfig,
  salvarConfig,
  agendarRetomada,
  removerRetomada,
  encerrar,
  caminhoExe,
  pastaBase: () => path.resolve(BASE)
};
