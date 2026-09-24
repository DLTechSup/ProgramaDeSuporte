import { Button, Point, keyboard, mouse } from "@nut-tree-fork/nut-js";
import type { InputInjector, PixelPoint, RemoteKeyboardEvent, RemoteMouseEvent } from "@nexodesk/shared";
import { KEY_CODE_MAP } from "./key-code-map";

const BUTTON_MAP: Record<NonNullable<RemoteMouseEvent["button"]>, Button> = {
  left: Button.LEFT,
  right: Button.RIGHT,
  middle: Button.MIDDLE,
};

function scrollSteps(delta: number): number {
  return Math.max(1, Math.round(Math.abs(delta)));
}

/** Injeta eventos de mouse/teclado no sistema operacional real usando nut-js. */
export class NutJsInputInjector implements InputInjector {
  async moveMouse(point: PixelPoint): Promise<void> {
    await mouse.setPosition(new Point(point.x, point.y));
  }

  async mouseButton(button: NonNullable<RemoteMouseEvent["button"]>, action: "down" | "up", point: PixelPoint): Promise<void> {
    await mouse.setPosition(new Point(point.x, point.y));
    const btn = BUTTON_MAP[button];
    if (action === "down") {
      await mouse.pressButton(btn);
    } else {
      await mouse.releaseButton(btn);
    }
  }

  async mouseWheel(deltaX: number, deltaY: number): Promise<void> {
    if (deltaY > 0) await mouse.scrollDown(scrollSteps(deltaY));
    else if (deltaY < 0) await mouse.scrollUp(scrollSteps(deltaY));
    if (deltaX > 0) await mouse.scrollRight(scrollSteps(deltaX));
    else if (deltaX < 0) await mouse.scrollLeft(scrollSteps(deltaX));
  }

  async keyEvent(event: RemoteKeyboardEvent): Promise<void> {
    const key = KEY_CODE_MAP[event.code];
    if (key === undefined) {
      console.warn(`[nexodesk-agent] Tecla nao suportada recebida do controlador: ${event.code}`);
      return;
    }
    if (event.kind === "down") {
      await keyboard.pressKey(key);
    } else {
      await keyboard.releaseKey(key);
    }
  }
}
