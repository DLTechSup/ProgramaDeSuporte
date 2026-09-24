import { generateChallengeNonce } from "./crypto";

/**
 * Mantem e gira o nonce de desafio usado na prova de senha (ver crypto.ts).
 * O dono deste objeto e sempre o AGENTE - nunca o servidor de sinalizacao,
 * que apenas guarda e repassa o valor atual para quem pedir. Isso garante que
 * uma prova de senha capturada em transito nao possa ser reaproveitada depois
 * que o agente decidir trocar o nonce (o que ele deve fazer apos toda
 * tentativa de conexao, com sucesso ou nao).
 */
export class ChallengeNonceRotator {
  private nonce: string;

  constructor(initial: string = generateChallengeNonce()) {
    this.nonce = initial;
  }

  get current(): string {
    return this.nonce;
  }

  rotate(): string {
    this.nonce = generateChallengeNonce();
    return this.nonce;
  }
}
