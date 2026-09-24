import { randomInt } from "node:crypto";

/**
 * Alfabeto sem caracteres ambiguos (sem 0/O, 1/I/l) para que o cliente consiga
 * ler a senha em voz alta ou digita-la sem erro ao passar por telefone/whatsapp.
 */
const READABLE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";

/**
 * Gera a senha de sessao "de uma vez" (one-time session password), no estilo
 * AnyDesk/TeamViewer: muda automaticamente a cada nova sessao (ou no intervalo
 * configurado), para que uma senha antiga vazada deixe de funcionar sozinha.
 */
export function generateSessionPassword(length = 6): string {
  return Array.from({ length }, () => READABLE_ALPHABET[randomInt(0, READABLE_ALPHABET.length)]).join("");
}

export interface PasswordStrengthResult {
  ok: boolean;
  problems: string[];
}

/**
 * Regras minimas para a "senha de acesso nao supervisionado" (fixa, opcional,
 * usada para acessar o mesmo computador repetidamente sem alguem na frente dele).
 * Bem mais rigorosa que a senha de sessao porque fica valida por muito mais tempo.
 */
export function checkUnattendedPasswordStrength(password: string): PasswordStrengthResult {
  const problems: string[] = [];
  if (password.length < 8) {
    problems.push("Use pelo menos 8 caracteres.");
  }
  if (!/[a-z]/.test(password)) {
    problems.push("Inclua ao menos uma letra minuscula.");
  }
  if (!/[A-Z]/.test(password)) {
    problems.push("Inclua ao menos uma letra maiuscula.");
  }
  if (!/[0-9]/.test(password)) {
    problems.push("Inclua ao menos um numero.");
  }
  return { ok: problems.length === 0, problems };
}
