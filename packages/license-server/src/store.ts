import type { PlanId } from "./plans";

export interface LicenseRecord {
  jti: string;
  email: string;
  plan: PlanId;
  issuedAt: Date;
  expiresAt: Date;
  revoked: boolean;
}

/**
 * Armazenamento em memoria - suficiente para desenvolvimento e para os testes
 * automatizados. Uma implantacao real deve trocar isto por um banco de dados
 * (Postgres, por exemplo) para que licencas e revogacoes sobrevivam a reinicios
 * e sejam compartilhadas entre varias instancias do servidor.
 */
export class LicenseStore {
  private readonly recordsByJti = new Map<string, LicenseRecord>();

  save(record: LicenseRecord): void {
    this.recordsByJti.set(record.jti, record);
  }

  isRevoked(jti: string): boolean {
    return this.recordsByJti.get(jti)?.revoked ?? false;
  }

  revoke(jti: string): boolean {
    const record = this.recordsByJti.get(jti);
    if (!record) return false;
    record.revoked = true;
    return true;
  }

  listByEmail(email: string): LicenseRecord[] {
    return Array.from(this.recordsByJti.values()).filter((r) => r.email === email);
  }

  get(jti: string): LicenseRecord | undefined {
    return this.recordsByJti.get(jti);
  }
}
