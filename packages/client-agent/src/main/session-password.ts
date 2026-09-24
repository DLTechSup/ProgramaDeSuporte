import { safeStorage } from "electron";
import { checkUnattendedPasswordStrength, generateSessionPassword, verifyPasswordProof, type PasswordStrengthResult } from "@nexodesk/shared";
import type { ConfigStore } from "./config-store";

/**
 * Controla as duas formas de senha do agente:
 *
 * 1. Senha de sessao: aleatoria, muda a cada rotacao (nova sessao, ou quando o
 *    cliente pede "gerar nova senha" na tela). Vive so em memoria.
 * 2. Senha de acesso nao supervisionado: fixa, opcional, definida pelo dono do
 *    computador para permitir reconectar sem alguem precisar ler o codigo na
 *    tela. Fica cifrada em disco com `safeStorage` (DPAPI/Keychain/libsecret).
 */
export class SessionPasswordManager {
  private currentSessionPassword: string;

  constructor(private readonly configStore: ConfigStore) {
    this.currentSessionPassword = generateSessionPassword();
  }

  get sessionPassword(): string {
    return this.currentSessionPassword;
  }

  rotateSessionPassword(): string {
    this.currentSessionPassword = generateSessionPassword();
    return this.currentSessionPassword;
  }

  hasUnattendedPassword(): boolean {
    return this.configStore.load().unattendedPasswordEncryptedBase64 !== null;
  }

  setUnattendedPassword(plainPassword: string): PasswordStrengthResult {
    const strength = checkUnattendedPasswordStrength(plainPassword);
    if (!strength.ok) {
      return strength;
    }
    if (!safeStorage.isEncryptionAvailable()) {
      return { ok: false, problems: ["A criptografia segura do sistema operacional nao esta disponivel nesta maquina."] };
    }
    const encrypted = safeStorage.encryptString(plainPassword);
    this.configStore.update({ unattendedPasswordEncryptedBase64: encrypted.toString("base64") });
    return { ok: true, problems: [] };
  }

  clearUnattendedPassword(): void {
    this.configStore.update({ unattendedPasswordEncryptedBase64: null });
  }

  private getUnattendedPasswordPlain(): string | null {
    const stored = this.configStore.load().unattendedPasswordEncryptedBase64;
    if (!stored) return null;
    return safeStorage.decryptString(Buffer.from(stored, "base64"));
  }

  /** Verifica a prova HMAC recebida contra a senha de sessao e, se houver, a senha fixa. */
  verifyProof(challengeNonce: string, proof: string): boolean {
    if (verifyPasswordProof(challengeNonce, this.currentSessionPassword, proof)) {
      return true;
    }
    const unattended = this.getUnattendedPasswordPlain();
    return unattended !== null && verifyPasswordProof(challengeNonce, unattended, proof);
  }
}
