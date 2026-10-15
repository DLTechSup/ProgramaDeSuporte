// Backup (exportacao) dos pacotes de driver antes de apagar.
const fs = require('fs');
const path = require('path');
const { BACKUP } = require('./caminhos.cjs');
const { executar, sys32 } = require('./powershell.cjs');
const { carimbo } = require('./carimbo.cjs');

function novaPasta() {
  const pasta = path.join(BACKUP, carimbo());
  fs.mkdirSync(pasta, { recursive: true });
  return pasta;
}

// pnputil /export-driver oemXX.inf "<pasta>\oemXX"
async function exportar(pastaBackup, pacote) {
  const destino = path.join(pastaBackup, pacote.replace(/\.inf$/i, ''));
  fs.mkdirSync(destino, { recursive: true });
  const r = await executar(sys32('pnputil.exe'), ['/export-driver', pacote, destino], { oem: true });
  return { ok: r.code === 0, destino, msg: (r.stderr || r.stdout).trim() };
}

function listar() {
  try {
    return fs
      .readdirSync(BACKUP, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => {
        const pasta = path.join(BACKUP, d.name);
        let pacotes = [];
        try {
          pacotes = fs.readdirSync(pasta, { withFileTypes: true }).filter((x) => x.isDirectory()).map((x) => x.name);
        } catch (_) {
          /* vazio */
        }
        return { nome: d.name, pasta, pacotes };
      })
      .sort((a, b) => b.nome.localeCompare(a.nome));
  } catch (_) {
    return [];
  }
}

// pnputil /add-driver "<pasta>\*.inf" /subdirs /install
async function restaurar(pasta) {
  const r = await executar(sys32('pnputil.exe'), ['/add-driver', path.join(pasta, '*.inf'), '/subdirs', '/install'], {
    oem: true,
    timeout: 180000
  });
  return { ok: r.code === 0 || r.code === 3010, msg: (r.stderr || r.stdout).trim().slice(-400) };
}

module.exports = { novaPasta, exportar, listar, restaurar };
