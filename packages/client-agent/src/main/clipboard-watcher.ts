import { clipboard } from "electron";
import { ClipboardEchoGuard } from "@nexodesk/shared";

const POLL_INTERVAL_MS = 600;

/**
 * O Electron nao expoe um evento nativo de "area de transferencia mudou" (o
 * proprio SO tambem nao tem uma API multiplataforma confiavel para isso), entao
 * observamos por sondagem (polling) em um intervalo curto o suficiente para
 * parecer instantaneo ao usuario, mas sem gastar CPU a toa.
 */
export class ClipboardWatcher {
  private readonly guard = new ClipboardEchoGuard();
  private timer: NodeJS.Timeout | null = null;
  private lastSeen = "";

  constructor(private readonly onLocalChange: (text: string) => void) {}

  start(): void {
    if (this.timer) return;
    this.lastSeen = clipboard.readText();
    this.timer = setInterval(() => this.poll(), POLL_INTERVAL_MS);
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  /** Chamado quando o outro lado da sessao manda um novo conteudo para aplicar aqui. */
  applyRemoteContent(text: string): void {
    this.guard.markApplied(text);
    clipboard.writeText(text);
    this.lastSeen = text;
  }

  private poll(): void {
    const current = clipboard.readText();
    if (current === this.lastSeen) return;
    this.lastSeen = current;
    if (this.guard.shouldForward(current)) {
      this.onLocalChange(current);
    }
  }
}
