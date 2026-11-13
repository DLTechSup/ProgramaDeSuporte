'use strict';
/* Processo principal: janelas, bandeja, monitor do WhatsApp e ponte com a interface (React). */
const { app, BrowserWindow, WebContentsView, ipcMain, dialog, shell, Tray, Menu, nativeImage, clipboard,
  powerSaveBlocker, screen, session } = require('electron');
const fs = require('fs');
const path = require('path');
const core = require('./core');
const tools = require('./tools');
const { Monitor } = require('./monitor');

// Continua monitorando com a janela minimizada/escondida.
for (const [k, v] of [['disable-renderer-backgrounding'], ['disable-background-timer-throttling'],
  ['disable-backgrounding-occluded-windows'], ['disable-features', 'CalculateNativeWinOcclusion']]) {
  app.commandLine.appendSwitch(k, v);
}
if (process.env.DEMANDA_DADOS) app.setPath('userData', process.env.DEMANDA_DADOS);
const WA_URL = process.env.DEMANDA_WA_URL || 'https://web.whatsapp.com';
const UA = `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${process.versions.chrome} Safari/537.36`;
const ICON = path.join(__dirname, 'icon.png');
const INDEX = path.join(__dirname, '..', '..', 'dist', 'index.html');

let cfg, store, hist, seen, monitor, mainWin, listWin, waView, monWin, tray;
let waPage = true, waModal = false;
const applyWaVisible = () => { if (waView) waView.setVisible(waPage && !waModal); };
let quitting = false, statusNow = { text: 'Iniciando...', level: 'wait' }, lastChats = [];
const logs = [];

if (!app.requestSingleInstanceLock()) { app.quit(); process.exit(0); }
app.on('second-instance', () => showMain());

// ------------------------------------------------------------------ estado
const toolsBase = () => process.env.CENTRAL_FERRAMENTAS || (app.isPackaged ? path.join(process.resourcesPath, 'ferramentas') : path.join(__dirname, '..', '..', 'ferramentas'));
const brandsNow = () => core.listBrands(cfg.get('pasta_marcas'), cfg.get('pastas_ignoradas'));
function snapshot() {
  const [pendentes, prontas] = store.counts();
  return { items: store.ordered(), pendentes, prontas, status: statusNow, cfg: cfg.data, brands: brandsNow(),
    detached: !!(listWin && !listWin.isDestroyed()), chats: lastChats, dedicated: !!cfg.get('sessao_dedicada') };
}
let pushTimer = null;
function push() {
  if (pushTimer) return;
  pushTimer = setTimeout(() => {
    pushTimer = null;
    for (const w of [mainWin, listWin]) if (w && !w.isDestroyed()) w.webContents.send('state', snapshot());
  }, 30);
}

// ----------------------------------------------------------------- janelas
const webPrefs = () => ({ preload: path.join(__dirname, 'preload.js'), contextIsolation: true, sandbox: true, backgroundThrottling: false });

function createMain() {
  const g = cfg.get('geometria_principal') || {};
  mainWin = new BrowserWindow({ width: g.width || 1400, height: g.height || 860, x: g.x, y: g.y, title: 'Central Informax', icon: ICON,
    backgroundColor: '#1b1d24', autoHideMenuBar: true, show: !process.env.DEMANDA_SMOKE, webPreferences: webPrefs() });
  mainWin.loadFile(INDEX);
  waView = new WebContentsView({ webPreferences: { partition: 'persist:wa', backgroundThrottling: false, contextIsolation: true, sandbox: true } });
  mainWin.contentView.addChildView(waView);
  setupSession('persist:wa');
  waView.webContents.setUserAgent(UA);
  waView.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
  waView.webContents.on('did-finish-load', () => addLog('WhatsApp Web carregado.'));
  waView.webContents.on('did-fail-load', (_e, code, desc) => { if (code !== -3) { addLog(`Falha ao carregar o WhatsApp Web (${desc}).`); setStatus('Sem conexão com o WhatsApp Web. Use “Recarregar”.', 'err'); } });
  waView.webContents.on('render-process-gone', () => { addLog('O navegador embutido parou. Recarregando...'); setTimeout(() => waView.webContents.reload(), 1000); });
  waView.webContents.loadURL(WA_URL, { userAgent: UA });
  mainWin.on('close', (e) => {
    if (quitting) return;
    e.preventDefault();
    mainWin.hide();
    if (tray && !cfg.get('aviso_bandeja')) { cfg.set('aviso_bandeja', true); tray.displayBalloon?.({ title: 'Central Informax', content: 'O programa continua monitorando em segundo plano. Para sair, use o ícone da bandeja.' }); }
  });
  mainWin.on('resized', saveMainBounds); mainWin.on('moved', saveMainBounds);
}
function saveMainBounds() { if (mainWin && !mainWin.isMinimized() && !mainWin.isMaximized()) cfg.set('geometria_principal', mainWin.getBounds()); }
function showMain() { if (!mainWin) return; if (mainWin.isMinimized()) mainWin.restore(); mainWin.show(); mainWin.focus(); }

function setupSession(partition) {
  const ses = session.fromPartition(partition);
  ses.setPermissionRequestHandler((_wc, perm, cb) => cb(['notifications', 'clipboard-read', 'clipboard-sanitized-write'].includes(perm)));
  ses.on('will-download', (_e, item) => item.setSavePath(path.join(app.getPath('downloads'), item.getFilename())));
}

function createList() {
  if (listWin && !listWin.isDestroyed()) { listWin.show(); return; }
  const g = cfg.get('geometria_lista');
  const wa = screen.getPrimaryDisplay().workArea;
  listWin = new BrowserWindow({ width: g?.width || 400, height: g?.height || Math.min(760, wa.height - 40),
    x: g?.x ?? wa.x + wa.width - 420, y: g?.y ?? wa.y + 20, title: 'Demanda do dia', icon: ICON, backgroundColor: '#1b1d24',
    autoHideMenuBar: true, alwaysOnTop: !!cfg.get('fixar_na_frente'), webPreferences: webPrefs() });
  listWin.loadFile(INDEX, { hash: 'lista' });
  const save = () => { if (listWin && !listWin.isDestroyed()) cfg.set('geometria_lista', listWin.getBounds()); };
  listWin.on('resized', save); listWin.on('moved', save);
  listWin.on('closed', () => { listWin = null; if (!quitting) cfg.set('lista_destacada', false); push(); });
  push();
}
function closeList() { if (listWin && !listWin.isDestroyed()) listWin.close(); }

function createTray() {
  tray = new Tray(nativeImage.createFromPath(ICON).resize({ width: 16, height: 16 }));
  tray.setToolTip('Central Informax');
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Abrir a Central', click: showMain },
    { label: 'Mostrar a lista', click: () => { cfg.set('lista_destacada', true); createList(); } },
    { type: 'separator' },
    { label: 'Sair (para de monitorar)', click: () => { if (confirmQuit()) { quitting = true; app.quit(); } } },
  ]));
  tray.on('click', showMain);
}
function confirmQuit() {
  return dialog.showMessageBoxSync({ type: 'question', buttons: ['Sair', 'Cancelar'], defaultId: 1, cancelId: 1, title: 'Sair',
    message: 'Se sair, o programa deixa de monitorar o grupo e a lista não recebe mais demandas.\nQuer mesmo sair?' }) === 0;
}

// --------------------------------------------------------------- monitor
const targetWc = () => (cfg.get('sessao_dedicada') && monWin && !monWin.isDestroyed() ? monWin.webContents : waView.webContents);
function ensureMonWin() {
  if (monWin && !monWin.isDestroyed()) { monWin.show(); return; }
  monWin = new BrowserWindow({ width: 1100, height: 800, title: 'WhatsApp — sessão do monitor (pode minimizar)', icon: ICON,
    autoHideMenuBar: true, webPreferences: { partition: 'persist:monitor', backgroundThrottling: false, contextIsolation: true, sandbox: true } });
  setupSession('persist:monitor');
  monWin.webContents.setUserAgent(UA);
  monWin.webContents.loadURL(WA_URL, { userAgent: UA });
  monWin.on('close', (e) => { if (!quitting) { e.preventDefault(); monWin.minimize(); } }); // fechar só minimiza: continua monitorando
}
function setupMonitor() {
  if (monitor) monitor.stop();
  const dedicated = !!cfg.get('sessao_dedicada');
  if (dedicated) ensureMonWin();
  monitor = new Monitor({ runJs: (code) => targetWc().executeJavaScript(code), cfg, store, hist, seen, dedicated });
  monitor.on('status', (t, l) => setStatus(t, l));
  monitor.on('changed', () => push());
  monitor.on('log', addLog);
  monitor.start();
}
function setStatus(text, level) { if (statusNow.text !== text || statusNow.level !== level) { statusNow = { text, level }; push(); } }
function addLog(text) { logs.push(`${new Date().toTimeString().slice(0, 8)}  ${text}`); if (logs.length > 500) logs.shift(); push(); }

// ------------------------------------------------------------- ações (IPC)
function addEntries(entries, site, atac, evento) {
  const root = cfg.get('pasta_marcas');
  let novas = 0, ja = 0;
  for (const { brand, ref, folder: given, line } of entries) {
    const folder = given || core.targetFolder(root, brand, ref, line);
    if (store.items.some((i) => path.resolve(i.folder) === path.resolve(folder))) { ja++; continue; }
    fs.mkdirSync(folder, { recursive: true });
    store.add({ brand: brand || '', ref, folder, saveDir: folder, sender: 'importada', photos: core.countPhotos(folder), site, atacado: atac,
      warn: brand ? [] : ['⚠ marca não reconhecida'] });
    hist.add(evento, brand || '(sem marca)', ref, core.countPhotos(folder), folder);
    novas++;
  }
  setStatus(`${novas} adicionada(s), ${ja} já estavam.`, 'ok'); push();
  return { novas, ja };
}

const actions = {
  state: () => snapshot(),
  clipboardText: () => clipboard.readText(),
  toggle: ({ id, field, value }) => {
    const d = store.get(id); if (!d) return;
    store.update(id, { [field]: !!value });
    const nome = field === 'site' ? 'Site' : 'Atacado';
    hist.add(value ? `${nome} marcado OK` : `${nome} desmarcado`, d.brand, d.ref, d.photos, d.folder); push();
  },
  open: (id) => { const d = store.get(id); if (d && fs.existsSync(d.folder)) shell.openPath(d.folder); },
  copy: (id) => { const d = store.get(id); if (d) clipboard.writeText(d.ref); },
  edit: ({ id, brand, ref }) => {
    const d = store.get(id); if (!d || !brand) return { ok: false, error: 'Escolha a marca.' };
    const root = cfg.get('pasta_marcas');
    const nf = core.targetFolder(root, brand, ref);
    try { core.moveFolder(d.folder, nf); } catch (e) { return { ok: false, error: `Não consegui mover a pasta: ${e.message}` }; }
    const sd = d.saveDir && d.saveDir.startsWith(d.folder) ? nf + d.saveDir.slice(d.folder.length) : nf;
    store.update(id, { brand, ref, folder: nf, saveDir: sd, photos: core.countPhotos(nf), warn: d.warn.filter((w) => !w.includes('marca') && !w.includes('revisar')) });
    hist.add('Editada', brand, ref, core.countPhotos(nf), nf); push(); return { ok: true };
  },
  remove: (id) => { const d = store.get(id); if (!d) return; store.remove(id); hist.add('Tirada da lista', d.brand, d.ref, d.photos, d.folder); push(); },
  add: ({ brand, ref }) => {
    const root = cfg.get('pasta_marcas'); if (!root || !brand || !ref) return { ok: false };
    const f = core.targetFolder(root, brand, ref); fs.mkdirSync(f, { recursive: true });
    store.add({ brand, ref, folder: f, saveDir: f, photos: core.countPhotos(f), sender: 'manual' });
    hist.add('Adicionada manualmente', brand, ref, core.countPhotos(f), f); push(); return { ok: true };
  },
  planPaste: (text) => core.planPaste(text, brandsNow(), store.ordered()),
  commitPaste: ({ text, site, atacado }) => addEntries(core.planPaste(text, brandsNow(), store.ordered()).filter((p) => p.status !== 'repetida')
    .map((p) => ({ brand: p.brand, ref: p.ref, line: p.line })), site, atacado, 'Colada (demandas de fora)'),
  importDirs: (brand) => {
    const base = path.join(cfg.get('pasta_marcas'), brand);
    try { return fs.readdirSync(base, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => ({ name: e.name, path: path.join(base, e.name), mtime: fs.statSync(path.join(base, e.name)).mtimeMs })).sort((a, b) => b.mtime - a.mtime); } catch { return []; }
  },
  commitImport: ({ brand, dirs, site, atacado }) => addEntries(dirs.map((d) => {
    const ref = core.norm(d.name).startsWith(core.norm(brand)) ? d.name.slice(brand.length).trim() : d.name;
    return { brand, ref, folder: d.path, line: d.name };
  }), site, atacado, 'Importada (demanda atual)'),
  pickFolder: async () => {
    const r = await dialog.showOpenDialog(mainWin, { properties: ['openDirectory'], title: 'Pasta principal das marcas' });
    return r.canceled ? null : r.filePaths[0];
  },
  setConfig: (patch) => {
    const before = { ...cfg.data }; cfg.patch(patch);
    if ('sessao_dedicada' in patch && patch.sessao_dedicada !== before.sessao_dedicada) setupMonitor();
    if ('lista_destacada' in patch && patch.lista_destacada !== before.lista_destacada) (patch.lista_destacada ? createList() : closeList());
    if ('fixar_na_frente' in patch && listWin) listWin.setAlwaysOnTop(!!patch.fixar_na_frente);
    if ('iniciar_com_windows' in patch) app.setLoginItemSettings({ openAtLogin: !!patch.iniciar_com_windows });
    push();
  },
  listChats: async () => { lastChats = await monitor.listChats(); push(); return lastChats; },
  confirmGroup: async ({ grupo, incluir }) => {
    cfg.patch({ grupo, monitorando: true, baseline_pendente: !incluir, inicio_ref: '', inicio_ok: false });
    hist.add('Grupo confirmado', grupo);
    const opened = await monitor.openChat(grupo);
    if (!opened) addLog(`Não achei “${grupo}” na lista de conversas; abra o grupo na mão.`);
    push(); return { opened };
  },
  stopMonitoring: () => { cfg.set('monitorando', false); hist.add('Monitoramento parado'); push(); },
  backToGroup: () => monitor.openChat(cfg.get('grupo')),
  markRef: (texto) => {
    const root = cfg.get('pasta_marcas'); if (!root) return { ok: false, error: 'Escolha a pasta das marcas.' };
    const [brand, ref, score] = core.splitCaption(texto, brandsNow());
    if (!store.findOpen(brand, ref)) {
      const folder = (brand && core.findRefFolder(root, brand, ref)) || core.targetFolder(root, brand, ref, texto);
      fs.mkdirSync(folder, { recursive: true });
      store.add({ brand: brand || '', ref, folder, saveDir: folder, sender: 'marcada', photos: core.countPhotos(folder),
        warn: brand ? (score >= 1 ? [] : ['⚠ revisar marca e referência']) : ['⚠ marca não reconhecida'] });
      hist.add('Marcada (estou fazendo)', brand || '(sem marca)', ref, core.countPhotos(folder), folder);
    }
    cfg.patch({ inicio_ref: texto, inicio_ok: false }); push();
    return { ok: true, brand: !!brand };
  },
  clearStart: () => { cfg.patch({ inicio_ref: '', inicio_ok: false }); hist.add('Ponto de partida removido'); push(); },
  history: () => hist.today(),
  logs: () => [...logs],
  summary: () => {
    const text = core.summaryText(store.ordered());
    const file = path.join(app.getPath('userData'), `Resumo ${core.todayISO().split('-').reverse().join('-')}.txt`);
    fs.writeFileSync(file, text, 'utf8'); clipboard.writeText(text); hist.add('Resumo do dia gerado'); shell.openPath(file);
    return { ok: true };
  },
  albumComplete: (id) => monitor.completeAlbum(id),
  reloadWa: () => { targetWc().reload(); setupMonitor(); },
  toggleDetach: () => actions.setConfig({ lista_destacada: !(listWin && !listWin.isDestroyed()) }),
  showMonitorWindow: () => { ensureMonWin(); },
  toolsList: () => tools.list(toolsBase()),
  toolOpen: (id) => tools.open(toolsBase(), id, (p) => shell.openPath(p)),
  toolCopy: async (id) => {
    const base = toolsBase();
    const name = tools.suggestedName(base, id); if (!name) return { ok: false, error: 'Esta ferramenta não está incluída nesta versão.' };
    const r = await dialog.showSaveDialog(mainWin, { defaultPath: path.join(app.getPath('desktop'), name), title: 'Salvar uma cópia' });
    if (r.canceled || !r.filePath) return { ok: false, canceled: true };
    return tools.copyTo(base, id, r.filePath);
  },
  openPath: (p) => { if (p && fs.existsSync(p)) shell.openPath(p); },
  openDataDir: () => shell.openPath(app.getPath('userData')),
  openBrandsDir: () => cfg.get('pasta_marcas') && shell.openPath(cfg.get('pasta_marcas')),
  quit: () => { if (confirmQuit()) { quitting = true; app.quit(); } },
};
ipcMain.handle('act', async (_e, name, arg) => (actions[name] ? actions[name](arg) : undefined));
ipcMain.on('waBounds', (_e, r) => { if (waView && r && r.width > 0) waView.setBounds({ x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) }); });
ipcMain.on('waVisible', (_e, v) => { waPage = !!v; applyWaVisible(); }); // a página atual usa o WhatsApp?
ipcMain.on('waModal', (_e, v) => { waModal = !!v; applyWaVisible(); }); // uma janelinha está aberta

// ------------------------------------------------------------------ início
app.whenReady().then(() => {
  const dir = app.getPath('userData');
  cfg = new core.Config(path.join(dir, 'config.json'));
  if (process.env.DEMANDA_CFG) cfg.patch(JSON.parse(process.env.DEMANDA_CFG));
  store = new core.Store(path.join(dir, 'lista.json'));
  hist = new core.History(path.join(dir, 'historico.jsonl'));
  seen = new core.Seen(path.join(dir, 'vistos.json'));
  powerSaveBlocker.start('prevent-app-suspension');
  Menu.setApplicationMenu(null);
  createMain();
  createTray();
  setupMonitor();
  if (cfg.get('lista_destacada')) createList();
  if (process.env.DEMANDA_SMOKE) runSmoke();
});
app.on('before-quit', () => { quitting = true; });
app.on('window-all-closed', () => { /* continua na bandeja */ });

// Teste de ponta a ponta (usado por scripts/smoke.js): salva o estado e imagens das janelas e sai.
async function runSmoke() {
  const out = process.env.DEMANDA_SMOKE;
  setTimeout(async () => {
    try {
      mainWin.show();
      const shot = async (w, f) => fs.writeFileSync(f, (await w.webContents.capturePage()).toPNG());
      await new Promise((r) => setTimeout(r, 1500));
      fs.writeFileSync(out + '.json', JSON.stringify({ snapshot: snapshot(), logs }, null, 2));
      await shot(mainWin, out + '-principal.png');
      if (listWin && !listWin.isDestroyed()) await shot(listWin, out + '-lista.png');
      const wa = await waView.webContents.capturePage(); fs.writeFileSync(out + '-whatsapp.png', wa.toPNG());
    } catch (e) { fs.writeFileSync(out + '.erro', String(e.stack || e)); }
    quitting = true; app.quit();
  }, Number(process.env.DEMANDA_SMOKE_MS || 9000));
}
