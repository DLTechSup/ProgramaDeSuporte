import { clipboard } from "electron";
import { ClipboardEchoGuard } from "@nexodesk/shared";

const POLL_INTERVAL_MS = 600;

/** Mesma estrategia de sondagem usada no Agent - ver o comentario la para o motivo. */
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
