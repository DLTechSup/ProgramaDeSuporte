// Log em arquivo (um por sessao) + memoria para o painel de log da tela.
const fs = require('fs');
const path = require('path');
const { LOGS } = require('./caminhos.cjs');

const buffer = [];
let ouvinte = null;
let arquivo = null;

const { carimbo } = require('./carimbo.cjs');

function abrirArquivo() {
  if (arquivo) return arquivo;
  try {
    fs.mkdirSync(LOGS, { recursive: true });
    arquivo = path.join(LOGS, `${carimbo()}.log`);
  } catch (_) {
    arquivo = null;
  }
  return arquivo;
}

function definirOuvinte(fn) {
  ouvinte = fn;
}

// { etapa, comando, item, resultado: OK|FALHA|AVISO|INFO, msg }
function registrar(entrada) {
  const e = {
    ts: new Date().toISOString(),
    etapa: entrada.etapa ?? '',
    comando: entrada.comando ?? '',
    item: entrada.item ?? '',
    resultado: entrada.resultado || 'INFO',
    msg: entrada.msg ?? ''
  };
  buffer.push(e);
  if (buffer.length > 2000) buffer.shift();
  const f = abrirArquivo();
  if (f) {
    const linha = [e.ts, `etapa=${e.etapa}`, e.resultado, e.comando, e.item, e.msg].join(' | ') + '\n';
    fs.appendFile(f, linha, () => {});
  }
  if (ouvinte) {
    try {
      ouvinte(e);
    } catch (_) {
      /* janela fechada */
    }
  }
  return e;
}

module.exports = { registrar, definirOuvinte, obter: () => buffer.slice(), pastaLogs: () => LOGS };
