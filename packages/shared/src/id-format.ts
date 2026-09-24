/**
 * Funcoes puras (sem dependencias do Node) de formatacao/validacao de ID.
 * Ficam separadas de `id-generator.ts` de proposito: este arquivo pode ser
 * importado com seguranca em codigo de navegador/renderer (ver `browser.ts`),
 * enquanto `id-generator.ts` depende de `node:crypto` e so roda em Node.
 */

/** Formata "123456789" como "123 456 789" para exibir de forma legivel ao cliente leigo. */
export function formatAgentId(agentId: string): string {
  const digitsOnly = agentId.replace(/\D/g, "");
  return digitsOnly.replace(/(\d{3})(?=\d)/g, "$1 ").trim();
}

/** Remove espacos/separadores digitados pelo usuario antes de usar o ID internamente. */
export function normalizeAgentId(input: string): string {
  return input.replace(/\D/g, "");
}

export function isValidAgentId(value: string): boolean {
  return /^\d{9}$/.test(normalizeAgentId(value));
}
