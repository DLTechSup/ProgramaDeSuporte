// Processo principal do Electron: admin, janela, IPC.
const { app, BrowserWindow, ipcMain, shell, dialog, clipboard, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const { executar, sys32, q } = require('./powershell.cjs');
const consultas = require('./consultas.cjs');
const acoes = require('./acoes.cjs');
const deteccao = require('./deteccao.cjs');
const backup = require('./backup.cjs');
const estado = require('./estado.cjs');
const log = require('./log.cjs');

const DEV = !!process.env.VITE_DEV;
const RETOMAR = process.argv.includes('--retomar');
let janela = null;

async function ehAdmin() {
  if (process.platform !== 'win32') return true;
  const r = await executar(sys32('fltmc.exe'), [], { timeout: 10000 });
  return r.code === 0;
}

// Sem administrador: relanca elevado (UAC) e fecha esta instancia.
async function garantirAdmin() {
  if (DEV || (await ehAdmin())) return true;
  if (process.argv.includes('--elevado')) {
    dialog.showErrorBox('Administrador necessario', 'O LimpadorUSB precisa ser executado como administrador.');
    return false;
  }
  const exe = estado.caminhoExe();
  const args = process.argv.slice(app.isPackaged ? 1 : 2).concat('--elevado');
  const lista = args.map((a) => q(a)).join(',');
  await executar(
    sys32('powershell.exe'),
    ['-NoProfile', '-WindowStyle', 'Hidden', '-Command', `Start-Process -FilePath ${q(exe)} -ArgumentList ${lista} -Verb RunAs`],
    { timeout: 60000 }
  );
  return false;
}

// Funcoes expostas para a interface (window.api.chamar(nome, ...args)).
const api = {
  // consultas
  painel: () => consultas.painel(),
  filas: () => consultas.filas(),
  fantasmas: () => consultas.fantasmas(),
  driversSpooler: () => consultas.driversSpooler(),
  pacotes: () => consultas.pacotes(),
  impressoras: () => consultas.impressoras(),
  processos: () => consultas.processos(),
  conectadasAgora: () => deteccao.conectadasAgora(),
  fotoFilas: () => deteccao.fotoFilas(),
  verificarNova: (base) => deteccao.verificar(base),
  // acoes
  removerFila: (n) => acoes.removerFila(n),
  removerFantasma: (id) => acoes.removerFantasma(id),
  removerDriverSpooler: (n) => acoes.removerDriverSpooler(n),
  removerPacote: (oem, pasta) => acoes.removerPacote(oem, pasta),
  reiniciarSpooler: () => acoes.reiniciarSpooler(),
  reiniciarComputador: () => acoes.reiniciarComputador(),
  pontoRestauracao: () => acoes.pontoRestauracao(),
  paginaTeste: (n) => acoes.paginaTeste(n),
  encerrarProcessos: (ids) => acoes.encerrarProcessos(ids),
  lerBloqueio: () => acoes.lerBloqueio(),
  definirBloqueio: (ligar) => acoes.definirBloqueio(ligar),
  restaurarBackup: (p) => acoes.restaurarBackup(p),
  abrirAtalho: (t) => acoes.abrirAtalho(t),
  // backup / estado / config
  novaPastaBackup: () => backup.novaPasta(),
  listarBackups: () => backup.listar(),
  estadoCarregar: () => estado.carregar(),
  estadoSalvar: (e) => estado.salvar(e),
  agendarRetomada: () => estado.agendarRetomada(),
  encerrarProcesso: () => estado.encerrar(),
  configCarregar: () => estado.carregarConfig(),
  configSalvar: (c) => estado.salvarConfig(c),
  // log
  logObter: () => log.obter(),
  logRegistrar: (e) => log.registrar(e),
  abrirPastaLogs: async () => {
    fs.mkdirSync(log.pastaLogs(), { recursive: true });
    return shell.openPath(log.pastaLogs());
  },
  // utilitarios
  info: () => ({ retomar: RETOMAR, plataforma: process.platform, versao: app.getVersion(), arquitetura: process.arch }),
  copiar: (t) => {
    clipboard.writeText(String(t));
    return true;
  },
  abrirPasta: async (p) => {
    if (!p) return 'Pasta nao configurada';
    return shell.openPath(p);
  },
  escolherPasta: async (titulo) => {
    const r = await dialog.showOpenDialog(janela, { title: titulo || 'Escolher pasta', properties: ['openDirectory'] });
    return r.canceled ? null : r.filePaths[0];
  }
};

ipcMain.handle('chamar', async (_e, nome, ...args) => {
  const fn = api[nome];
  if (!fn) return { ok: false, erro: 'Funcao desconhecida: ' + nome };
  try {
    return { ok: true, dados: await fn(...args) };
  } catch (e) {
    log.registrar({ comando: nome, resultado: 'FALHA', msg: e && e.message });
    return { ok: false, erro: (e && e.message) || String(e) };
  }
});

function criarJanela() {
  janela = new BrowserWindow({
    width: 1000,
    height: 680,
    minWidth: 860,
    minHeight: 600,
    backgroundColor: '#0a1020',
    title: 'Limpador USB de Impressoras',
    autoHideMenuBar: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });
  Menu.setApplicationMenu(null);
  janela.once('ready-to-show', () => janela.show());
  janela.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  log.definirOuvinte((e) => {
    if (janela && !janela.isDestroyed()) janela.webContents.send('log', e);
  });
  if (DEV) janela.loadURL('http://localhost:5173');
  else janela.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
}

// Excecao nao tratada: grava no log e avisa sem fechar o programa.
function tratarExcecao(err) {
  const texto = (err && err.stack) || String(err);
  log.registrar({ comando: 'excecao', resultado: 'FALHA', msg: texto });
  try {
    dialog.showErrorBox('Algo deu errado', 'Ocorreu um erro inesperado, mas o programa continua aberto.\nOs detalhes foram gravados no log.');
  } catch (_) {
    /* ignora */
  }
}
process.on('uncaughtException', tratarExcecao);
process.on('unhandledRejection', tratarExcecao);

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (janela) {
      if (janela.isMinimized()) janela.restore();
      janela.focus();
    }
  });
  app.whenReady().then(async () => {
    if (!(await garantirAdmin())) {
      app.quit();
      return;
    }
    log.registrar({ comando: 'inicio', resultado: 'INFO', msg: `LimpadorUSB ${app.getVersion()} (${process.arch})${RETOMAR ? ' --retomar' : ''}` });
    criarJanela();
  });
  app.on('window-all-closed', () => app.quit());
}
