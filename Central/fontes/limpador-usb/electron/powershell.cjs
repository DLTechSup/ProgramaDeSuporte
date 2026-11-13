// Execucao de PowerShell e de executaveis do sistema, sem janela de console.
const { spawn } = require('child_process');
const path = require('path');

const TIMEOUT_PADRAO = 60000;

// Em Windows de 64 bits com o app de 32 bits, System32 e redirecionado para
// SysWOW64. Usar Sysnative garante o powershell/pnputil de 64 bits.
function sys32(exe) {
  if (process.platform !== 'win32') return exe;
  const win = process.env.windir || process.env.SystemRoot || 'C:\\Windows';
  const sub = process.arch === 'ia32' && process.env.PROCESSOR_ARCHITEW6432 ? 'Sysnative' : 'System32';
  if (exe.toLowerCase() === 'powershell.exe') {
    return path.join(win, sub, 'WindowsPowerShell', 'v1.0', 'powershell.exe');
  }
  return path.join(win, sub, exe);
}

function decodificar(buf, oem) {
  if (!buf.length) return '';
  if (oem) {
    try {
      return new TextDecoder('ibm850').decode(buf);
    } catch (_) {
      /* cai para utf-8 */
    }
  }
  return buf.toString('utf8').replace(/^\uFEFF/, '');
}

// Roda um executavel e devolve { code, stdout, stderr, timeout }.
function executar(arquivo, args = [], { timeout = TIMEOUT_PADRAO, oem = false } = {}) {
  return new Promise((resolve) => {
    let filho;
    try {
      filho = spawn(arquivo, args, { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    } catch (e) {
      resolve({ code: -1, stdout: '', stderr: String(e.message || e), timeout: false });
      return;
    }
    const out = [];
    const err = [];
    let estourou = false;
    let fim = false;
    const fechar = (code) => {
      if (fim) return;
      fim = true;
      clearTimeout(timer);
      resolve({
        code,
        stdout: decodificar(Buffer.concat(out), oem),
        stderr: decodificar(Buffer.concat(err), oem),
        timeout: estourou
      });
    };
    const timer = setTimeout(() => {
      estourou = true;
      try {
        filho.kill();
      } catch (_) {
        /* ignora */
      }
      setTimeout(() => fechar(-1), 500);
    }, timeout);
    filho.stdout.on('data', (d) => out.push(d));
    filho.stderr.on('data', (d) => err.push(d));
    filho.on('error', (e) => {
      err.push(Buffer.from(String(e.message || e)));
      fechar(-1);
    });
    filho.on('close', (code) => fechar(code === null ? -1 : code));
  });
}

const PREFIXO =
  "[Console]::OutputEncoding = [Text.Encoding]::UTF8; $ProgressPreference = 'SilentlyContinue'; ";

// powershell -NoProfile -ExecutionPolicy Bypass (o comando vai codificado em
// base64 para nao haver problema de aspas/acentos).
function rodarPS(comando, opcoes) {
  const codificado = Buffer.from(PREFIXO + comando, 'utf16le').toString('base64');
  return executar(
    sys32('powershell.exe'),
    ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', codificado],
    opcoes
  );
}

function normalizarLista(valor) {
  if (valor === null || valor === undefined) return [];
  return Array.isArray(valor) ? valor : [valor];
}

// Executa uma consulta e devolve SEMPRE uma lista de objetos (ConvertTo-Json).
async function executarPS(comando, opcoes) {
  const script =
    "$ErrorActionPreference = 'Stop'; try { $r = @(" +
    comando +
    "); if ($r.Count -eq 0) { '[]' } else { ConvertTo-Json -InputObject $r -Depth 4 -Compress } } " +
    'catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }';
  const r = await rodarPS(script, opcoes);
  if (r.timeout) throw new Error('Tempo esgotado (60 s) ao consultar o sistema.');
  if (r.code !== 0) throw new Error((r.stderr || r.stdout || 'Falha no PowerShell').trim());
  const texto = r.stdout.trim();
  if (!texto) return [];
  try {
    return normalizarLista(JSON.parse(texto));
  } catch (e) {
    throw new Error('Resposta invalida do PowerShell: ' + texto.slice(0, 200));
  }
}

// Executa uma acao (sem retorno de dados). ok = codigo 0.
async function acaoPS(comando, opcoes) {
  const script =
    "$ErrorActionPreference = 'Stop'; try { " +
    comando +
    " } catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }";
  const r = await rodarPS(script, opcoes);
  return {
    ok: r.code === 0 && !r.timeout,
    code: r.code,
    stdout: r.stdout.trim(),
    msg: r.timeout ? 'Tempo esgotado (60 s)' : (r.stderr || '').trim()
  };
}

// Literal de string do PowerShell entre aspas simples.
const q = (s) => "'" + String(s).replace(/'/g, "''") + "'";

module.exports = { sys32, executar, rodarPS, executarPS, acaoPS, normalizarLista, q, TIMEOUT_PADRAO };
