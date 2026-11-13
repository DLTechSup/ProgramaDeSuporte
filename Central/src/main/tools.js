'use strict';
/* Catálogo das ferramentas que vêm dentro da Central (no mesmo instalador).
 * Cada uma fica em <ferramentas>/<id>/ e abre na sua própria janela. */
const fs = require('fs');
const path = require('path');

const INSTALADOR = /instalador.*\.exe$/i;
const TOOLS = [
  { id: 'suporte-tecnico', grupo: 'Atendimento', nome: 'Suporte remoto — Técnico', pattern: INSTALADOR, rotulo: 'Abrir / instalar',
    desc: 'Acessa o computador do cliente com ID e senha. Na primeira vez, instale; depois use o atalho criado.' },
  { id: 'suporte-cliente', grupo: 'Atendimento', nome: 'Suporte remoto — Cliente', pattern: INSTALADOR, acao: 'copiar', rotulo: 'Salvar cópia...',
    desc: 'Instalador para o computador do cliente (mostra só o ID e a senha). Salve uma cópia para entregar.' },
  { id: 'limpador-usb', grupo: 'Atendimento', nome: 'Limpador USB de impressoras', pattern: /\.exe$/i,
    desc: 'Libera as portas USB virtuais antes de resetar impressoras.' },
  { id: 'editor-fotos', grupo: 'Fotos', nome: 'Editor de Fotos', pattern: /\.exe$/i,
    desc: 'Coloca códigos e cores nas fotos dos calçados e salva cada foto com o nome da cor.' },
  { id: 'separador-fotos', grupo: 'Fotos', nome: 'Separador de Fotos', exe: 'SeparadorFotos.exe',
    desc: 'Lê a etiqueta (OCR) de cada foto e separa por marca e referência.' },
  { id: 'renomeador', grupo: 'Fotos', nome: 'Renomeador em Massa', exe: 'RenomeadorEmMassa.exe',
    desc: 'Fica na bandeja. Selecione arquivos no Explorador, aperte Ctrl+Alt+R e renomeie com numeração.' },
  { id: 'nomes-calcados', grupo: 'Cadastro', nome: 'Nomes e Descrições de Calçados', exe: 'NomesCalcados.exe',
    desc: 'Cria nomes e descrições para a Nuvemshop seguindo as regras, com IA grátis ou modo offline.' },
  { id: 'monitor-demandas', grupo: 'Cadastro', nome: 'Monitor de Demandas (versão Python)', exe: 'MonitorDeDemandas.exe',
    desc: 'Monitor de grupos do WhatsApp feito antes da Demanda do Dia, com lista em arquivo .txt.' },
  { id: 'captura-tela', grupo: 'Utilitários', nome: 'Captura de Tela', exe: 'CapturaDeTela.exe',
    desc: 'Fica na bandeja. Os dois botões do mouse juntos e arraste: salva e copia a imagem.' },
  { id: 'executar-py', grupo: 'Utilitários', nome: 'Executar .py', pattern: INSTALADOR, rotulo: 'Instalar',
    desc: 'Duplo clique em qualquer .py abre um console e mostra o resultado. Precisa do Python instalado.' },
];

// Ainda não estão no repositório: precisam do código (ou do que o programa já faz).
const PENDENTES = [
  { nome: 'Grade Fácil', desc: 'Aguardando o código para entrar na Central.' },
  { nome: 'Note Deck', desc: 'Aguardando o código para entrar na Central (e ligar com a lista da Demanda do Dia).' },
];

function resolveExe(base, tool) {
  const dir = path.join(base, tool.id);
  let files = [];
  try { files = fs.readdirSync(dir, { withFileTypes: true }).filter((e) => e.isFile()).map((e) => e.name); } catch { return null; }
  if (tool.exe) { const f = files.find((n) => n.toLowerCase() === tool.exe.toLowerCase()); return f ? path.join(dir, f) : null; }
  if (tool.pattern) {
    const f = files.filter((n) => tool.pattern.test(n) && !/uninstall|desinstal/i.test(n)).sort((a, b) => a.length - b.length)[0];
    return f ? path.join(dir, f) : null;
  }
  return null;
}

const strip = ({ pattern, exe, ...t }) => t; // não manda regex pela ponte

function list(base) {
  return {
    tools: TOOLS.map((t) => ({ ...strip(t), acao: t.acao || 'abrir', rotulo: t.rotulo || 'Abrir', incluido: !!resolveExe(base, t) })),
    pendentes: PENDENTES,
  };
}

/** @param {(p:string)=>Promise<string>|string} openPath  shell.openPath (usa o Windows, então pede UAC se preciso) */
async function open(base, id, openPath) {
  const t = TOOLS.find((x) => x.id === id);
  const exe = t && resolveExe(base, t);
  if (!exe) return { ok: false, error: 'Esta ferramenta não está incluída nesta versão.' };
  const err = await openPath(exe);
  return err ? { ok: false, error: String(err) } : { ok: true };
}

function copyTo(base, id, destination) {
  const t = TOOLS.find((x) => x.id === id);
  const exe = t && resolveExe(base, t);
  if (!exe) return { ok: false, error: 'Esta ferramenta não está incluída nesta versão.' };
  fs.copyFileSync(exe, destination);
  return { ok: true };
}
const suggestedName = (base, id) => { const t = TOOLS.find((x) => x.id === id); const exe = t && resolveExe(base, t); return exe ? path.basename(exe) : ''; };

module.exports = { TOOLS, PENDENTES, resolveExe, list, open, copyTo, suggestedName };
