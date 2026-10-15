// Ponte com o processo principal (Electron). Fora do Electron (navegador)
// usa dados de demonstração para poder visualizar a interface.
import { mock } from './mock.js';

const real = typeof window !== 'undefined' ? window.api : undefined;

export const emElectron = !!real;

export async function chamar(nome, ...args) {
  if (real) {
    const r = await real.chamar(nome, ...args);
    if (!r.ok) throw new Error(r.erro);
    return r.dados;
  }
  return mock(nome, ...args);
}

export function aoLogar(cb) {
  return real ? real.aoLogar(cb) : () => {};
}
