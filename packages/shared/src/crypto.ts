import { createHash, createHmac, randomBytes, scryptSync, timingSafeEqual } from "node:crypto";

/**
 * Gera um nonce de desafio de uso unico. O agente publica um novo nonce a cada
 * conexao (e descarta o antigo assim que usado), para que a prova de senha
 * relayada pelo servidor de sinalizacao nunca possa ser reaproveitada
 * ("replay attack") por quem eventualmente a observar em transito.
 */
export function generateChallengeNonce(): string {
  return randomBytes(16).toString("hex");
}

/**
 * Calcula a prova de senha: HMAC-SHA256(chave = senha, mensagem = nonce).
 * Isso e o que trafega pela rede no lugar da senha em texto puro - o servidor
 * de sinalizacao so ve este valor e nunca consegue voltar a senha original a
 * partir dele.
 */
export function computePasswordProof(challengeNonce: string, password: string): string {
  return createHmac("sha256", password).update(challengeNonce).digest("hex");
}

/** Compara duas provas em tempo constante, evitando ataques de temporizacao. */
export function verifyPasswordProof(challengeNonce: string, password: string, proof: string): boolean {
  const expected = computePasswordProof(challengeNonce, password);
  const expectedBuf = Buffer.from(expected, "hex");
  const proofBuf = Buffer.from(proof, "hex");
  if (expectedBuf.length !== proofBuf.length) return false;
  return timingSafeEqual(expectedBuf, proofBuf);
}

export interface HashedPassword {
  algorithm: "scrypt";
  salt: string;
  hash: string;
}

/**
 * Usado apenas para guardar em disco a senha fixa de "acesso nao supervisionado"
 * do agente (nunca a senha de sessao, que so existe em memoria). O agente
 * guarda o hash, nunca a senha em texto puro.
 */
export function hashPasswordForStorage(password: string): HashedPassword {
  const salt = randomBytes(16).toString("hex");
  const hash = scryptSync(password, salt, 64).toString("hex");
  return { algorithm: "scrypt", salt, hash };
}

export function verifyStoredPassword(password: string, stored: HashedPassword): boolean {
  const candidate = scryptSync(password, stored.salt, 64);
  const expected = Buffer.from(stored.hash, "hex");
  if (candidate.length !== expected.length) return false;
  return timingSafeEqual(candidate, expected);
}

export function sha256Hex(data: Buffer): string {
  return createHash("sha256").update(data).digest("hex");
}
