import { randomInt } from "node:crypto";

export { formatAgentId, isValidAgentId, normalizeAgentId } from "./id-format";

/**
 * Gera um ID publico no formato "000 000 000" (9 digitos, como o usado por
 * ferramentas de acesso remoto conhecidas). O ID e apenas um apelido de
 * roteamento no servidor de sinalizacao - ele nao concede acesso a nada
 * sozinho, a senha e sempre exigida.
 *
 * So roda em Node (usa `node:crypto`) - por isso fica separado de `id-format.ts`.
 */
export function generateAgentId(): string {
  const digits = Array.from({ length: 9 }, () => randomInt(0, 10)).join("");
  return digits;
}
