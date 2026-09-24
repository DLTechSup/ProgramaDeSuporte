import type { RemoteInputEvent, RemoteKeyboardEvent, RemoteMouseEvent } from "./protocol";

export interface ScreenSize {
  width: number;
  height: number;
}

export interface PixelPoint {
  x: number;
  y: number;
}

/**
 * O controlador envia coordenadas normalizadas (0..1) porque a tela do cliente
 * pode ter uma resolucao diferente da tela (ou da janela de visualizacao) do
 * tecnico. O agente converte para pixels reais da SUA propria tela antes de
 * injetar o evento.
 */
export function denormalizePoint(event: Pick<RemoteMouseEvent, "x" | "y">, screen: ScreenSize): PixelPoint {
  const clamp01 = (n: number) => Math.min(1, Math.max(0, n));
  return {
    x: Math.round(clamp01(event.x) * screen.width),
    y: Math.round(clamp01(event.y) * screen.height),
  };
}

export function normalizePoint(point: PixelPoint, screen: ScreenSize): { x: number; y: number } {
  return {
    x: screen.width === 0 ? 0 : point.x / screen.width,
    y: screen.height === 0 ? 0 : point.y / screen.height,
  };
}

/**
 * Interface que qualquer backend de injecao de input do sistema operacional
 * (ex.: nut-js no Windows/macOS/Linux) precisa implementar. Mantida separada
 * da biblioteca concreta para que o dispatcher abaixo seja testavel sem
 * depender de automacao real de SO.
 */
export interface InputInjector {
  moveMouse(point: PixelPoint): Promise<void>;
  mouseButton(button: NonNullable<RemoteMouseEvent["button"]>, action: "down" | "up", point: PixelPoint): Promise<void>;
  mouseWheel(deltaX: number, deltaY: number): Promise<void>;
  keyEvent(event: RemoteKeyboardEvent): Promise<void>;
}

/**
 * Traduz eventos do protocolo (coordenadas normalizadas) para chamadas no
 * injetor de input real (coordenadas em pixels da tela do agente). Isolar essa
 * logica do restante do app Electron permite testa-la com um injetor falso.
 */
export class RemoteInputDispatcher {
  constructor(
    private readonly injector: InputInjector,
    private readonly getScreenSize: () => ScreenSize
  ) {}

  async dispatch(event: RemoteInputEvent): Promise<void> {
    if (event.type === "input-mouse") {
      return this.dispatchMouse(event);
    }
    return this.injector.keyEvent(event);
  }

  private async dispatchMouse(event: RemoteMouseEvent): Promise<void> {
    const point = denormalizePoint(event, this.getScreenSize());
    switch (event.kind) {
      case "move":
        return this.injector.moveMouse(point);
      case "down":
        if (!event.button) throw new Error("Evento mouse-down sem botao definido.");
        return this.injector.mouseButton(event.button, "down", point);
      case "up":
        if (!event.button) throw new Error("Evento mouse-up sem botao definido.");
        return this.injector.mouseButton(event.button, "up", point);
      case "wheel":
        return this.injector.mouseWheel(event.deltaX ?? 0, event.deltaY ?? 0);
      default:
        throw new Error(`Tipo de evento de mouse desconhecido: ${(event as RemoteMouseEvent).kind}`);
    }
  }
}
