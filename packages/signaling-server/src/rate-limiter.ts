/**
 * Limitador simples de tentativas (janela deslizante por chave). Usado para
 * impedir forca bruta de senha via `connect-request`: sem isso, alguem poderia
 * tentar milhares de senhas de 6 caracteres por segundo contra um ID conhecido.
 */
export class RateLimiter {
  private readonly hitsByKey = new Map<string, number[]>();

  constructor(
    private readonly maxHits: number,
    private readonly windowMs: number
  ) {}

  /** Retorna true se a tentativa deve ser permitida, e ja registra o hit. */
  allow(key: string, now: number = Date.now()): boolean {
    const windowStart = now - this.windowMs;
    const existing = this.hitsByKey.get(key) ?? [];
    const recent = existing.filter((t) => t > windowStart);
    if (recent.length >= this.maxHits) {
      this.hitsByKey.set(key, recent);
      return false;
    }
    recent.push(now);
    this.hitsByKey.set(key, recent);
    return true;
  }

  reset(key: string): void {
    this.hitsByKey.delete(key);
  }
}
