import { useEffect, useRef } from 'react';

// Executa fn a cada "ms" (esperando a anterior terminar). Para quando ativo=false.
export function usePolling(fn, ms, ativo, deps = []) {
  const ref = useRef(fn);
  ref.current = fn;
  useEffect(() => {
    if (!ativo) return undefined;
    let parar = false;
    let timer;
    const ciclo = async () => {
      try {
        await ref.current();
      } catch (_) {
        /* erro ja tratado pelo chamador */
      }
      if (!parar) timer = setTimeout(ciclo, ms);
    };
    ciclo();
    return () => {
      parar = true;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ativo, ms, ...deps]);
}

export const norm = (s) => String(s || '').toLowerCase();

export function bate(filtro, ...textos) {
  const f = norm(filtro).trim();
  if (!f) return false;
  return textos.some((t) => norm(t).includes(f));
}

export function plural(n, um, varios) {
  return `${n} ${n === 1 ? um : varios}`;
}

export function nomeArquivo(caminho) {
  return String(caminho || '').split(/[\\/]/).pop();
}

export const STATUS_PT = {
  Normal: 'Normal',
  Offline: 'Offline',
  Error: 'Erro',
  Paused: 'Pausada',
  PaperJam: 'Papel atolado',
  PaperOut: 'Sem papel',
  Printing: 'Imprimindo',
  Livre: 'Livre'
};
