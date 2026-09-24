import { createHash } from "node:crypto";

function hashContent(content: string): string {
  return createHash("sha256").update(content).digest("hex");
}

/**
 * Evita o "eco infinito" da sincronizacao de area de transferencia: sem isso,
 * quando o agente aplica uma mudanca de clipboard vinda do controlador, o
 * monitor local de clipboard do agente detectaria essa mesma mudanca e a
 * reenviaria de volta ao controlador, que a reenviaria de novo, para sempre.
 */
export class ClipboardEchoGuard {
  private lastAppliedHash: string | null = null;

  /** Chame isto ao APLICAR um conteudo vindo da outra ponta, antes de escrever no clipboard do SO. */
  markApplied(content: string): void {
    this.lastAppliedHash = hashContent(content);
  }

  /**
   * Chame isto quando o monitor local detectar uma mudanca no clipboard do SO.
   * Retorna false se essa mudanca foi causada por markApplied() (nao deve ser reenviada).
   */
  shouldForward(content: string): boolean {
    const hash = hashContent(content);
    if (hash === this.lastAppliedHash) {
      return false;
    }
    return true;
  }
}
