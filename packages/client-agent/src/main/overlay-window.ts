import { join } from "node:path";
import { BrowserWindow, globalShortcut, screen } from "electron";

const EMERGENCY_SHORTCUT = "Control+Alt+Shift+F9";

/**
 * Janela de "tela preta de privacidade": cobre a tela toda para que o cliente
 * nao fique mexendo enquanto o tecnico trabalha, sem que o cliente veja o que
 * esta sendo feito. O tecnico pode desativar a qualquer momento pelo
 * Controlador, e o cliente SEMPRE pode encerrar por conta propria com o atalho
 * de emergencia - isso e proposital: o cliente nunca fica de fato "trancado
 * para fora" do proprio computador.
 *
 * Limitacao conhecida do MVP: cobre apenas o monitor principal. Configuracoes
 * com varios monitores exigem uma janela por monitor (ver docs/ROTEIRO.md).
 */
export class PrivacyOverlay {
  private window: BrowserWindow | null = null;

  constructor(private readonly onEmergencyEnd: () => void) {}

  show(): void {
    if (this.window) return;

    const { bounds } = screen.getPrimaryDisplay();
    const window = new BrowserWindow({
      x: bounds.x,
      y: bounds.y,
      width: bounds.width,
      height: bounds.height,
      frame: false,
      fullscreen: true,
      alwaysOnTop: true,
      skipTaskbar: true,
      resizable: false,
      movable: false,
      closable: false,
      minimizable: false,
      maximizable: false,
      backgroundColor: "#000000",
      webPreferences: { contextIsolation: true, nodeIntegration: false },
    });
    window.setAlwaysOnTop(true, "screen-saver");
    window.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
    window.loadFile(join(__dirname, "..", "renderer", "overlay", "index.html"));
    window.on("closed", () => {
      this.window = null;
    });
    this.window = window;

    globalShortcut.register(EMERGENCY_SHORTCUT, () => {
      this.hide();
      this.onEmergencyEnd();
    });
  }

  hide(): void {
    if (globalShortcut.isRegistered(EMERGENCY_SHORTCUT)) {
      globalShortcut.unregister(EMERGENCY_SHORTCUT);
    }
    if (this.window) {
      this.window.destroy();
      this.window = null;
    }
  }

  get isVisible(): boolean {
    return this.window !== null;
  }
}
