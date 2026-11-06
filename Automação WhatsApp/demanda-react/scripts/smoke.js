'use strict';
/* Teste de ponta a ponta com o Electron de verdade (precisa de tela; no Linux use xvfb-run).
 * Abre o programa apontando para uma página que imita o WhatsApp Web e confere o resultado.
 * Uso: xvfb-run -a node scripts/smoke.js [pasta-de-saida] */
const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { pathToFileURL } = require('url');
const electron = require('electron');

const base = fs.mkdtempSync(path.join(os.tmpdir(), 'smoke-'));
const outDir = process.argv[2] ? path.resolve(process.argv[2]) : base;
fs.mkdirSync(outDir, { recursive: true });
const root = path.join(base, 'LANÇAMENTOS');
for (const b of ['BEIRA RIO', 'BEBECÊ', 'DAKOTA']) fs.mkdirSync(path.join(root, b), { recursive: true });
const docked = process.env.SMOKE_MODE === 'docked'; // só tira fotos da tela: lista encaixada, grupo ainda não escolhido
const cfg = { pasta_marcas: root, grupo: 'PROGRAMAÇÃO ✨📷💰', monitorando: !docked, baseline_pendente: false, lista_destacada: !docked, intervalo_seg: 1 };
const env = { ...process.env, DEMANDA_DADOS: path.join(base, 'dados'), DEMANDA_CFG: JSON.stringify(cfg), DEMANDA_SMOKE: path.join(outDir, 'smoke'),
  DEMANDA_WA_URL: pathToFileURL(path.join(__dirname, '..', 'test', 'fixtures', 'fake_wa.html')).href, DEMANDA_SMOKE_MS: '9000' };
const r = spawnSync(electron, ['--no-sandbox', '--disable-gpu', path.join(__dirname, '..')], { env, encoding: 'utf8', timeout: 90000 });
const f = path.join(outDir, 'smoke.json');
if (!fs.existsSync(f)) { console.error('Sem resultado.\n', (r.stderr || '').slice(-1500)); process.exit(1); }
const { snapshot, logs } = JSON.parse(fs.readFileSync(f, 'utf8'));
const itens = snapshot.items.map((d) => `${d.brand || '(sem marca)'} | ${d.ref} | ${d.photos} foto(s)`);
console.log('Status:', snapshot.status.text);
console.log('Itens:', itens);
console.log('Lista destacada aberta:', snapshot.detached);
if (docked) { console.log('Fotos da tela salvas em', outDir); process.exit(0); }
const ok = itens.length === 3 && snapshot.status.level === 'ok' && fs.existsSync(path.join(root, 'BEIRA RIO', 'BEIRA RIO 8513.115', 'foto_01.jpg')) && snapshot.detached;
console.log(ok ? 'SMOKE OK' : 'SMOKE FALHOU\n' + logs.join('\n'));
process.exit(ok ? 0 : 1);
