import assert from "node:assert/strict";
import { test } from "node:test";
import type { InputInjector, PixelPoint } from "../src/remote-input";
import { RemoteInputDispatcher, denormalizePoint, normalizePoint } from "../src/remote-input";
import type { RemoteKeyboardEvent } from "../src/protocol";

class FakeInjector implements InputInjector {
  moves: PixelPoint[] = [];
  buttons: { button: string; action: string; point: PixelPoint }[] = [];
  wheels: { deltaX: number; deltaY: number }[] = [];
  keys: RemoteKeyboardEvent[] = [];

  async moveMouse(point: PixelPoint): Promise<void> {
    this.moves.push(point);
  }
  async mouseButton(button: "left" | "right" | "middle", action: "down" | "up", point: PixelPoint): Promise<void> {
    this.buttons.push({ button, action, point });
  }
  async mouseWheel(deltaX: number, deltaY: number): Promise<void> {
    this.wheels.push({ deltaX, deltaY });
  }
  async keyEvent(event: RemoteKeyboardEvent): Promise<void> {
    this.keys.push(event);
  }
}

test("denormalizePoint converte coordenadas 0..1 para pixels e limita fora da faixa", () => {
  const screen = { width: 1920, height: 1080 };
  assert.deepEqual(denormalizePoint({ x: 0.5, y: 0.5 }, screen), { x: 960, y: 540 });
  assert.deepEqual(denormalizePoint({ x: -1, y: 2 }, screen), { x: 0, y: 1080 });
});

test("normalizePoint e o inverso aproximado de denormalizePoint", () => {
  const screen = { width: 1000, height: 500 };
  const normalized = normalizePoint({ x: 250, y: 125 }, screen);
  assert.deepEqual(normalized, { x: 0.25, y: 0.25 });
});

test("RemoteInputDispatcher despacha movimento de mouse convertido para pixels", async () => {
  const injector = new FakeInjector();
  const dispatcher = new RemoteInputDispatcher(injector, () => ({ width: 800, height: 600 }));
  await dispatcher.dispatch({ type: "input-mouse", kind: "move", x: 0.5, y: 0.5 });
  assert.deepEqual(injector.moves, [{ x: 400, y: 300 }]);
});

test("RemoteInputDispatcher despacha clique com botao", async () => {
  const injector = new FakeInjector();
  const dispatcher = new RemoteInputDispatcher(injector, () => ({ width: 800, height: 600 }));
  await dispatcher.dispatch({ type: "input-mouse", kind: "down", x: 0, y: 0, button: "left" });
  assert.equal(injector.buttons.length, 1);
  assert.equal(injector.buttons[0]?.button, "left");
  assert.equal(injector.buttons[0]?.action, "down");
});

test("RemoteInputDispatcher rejeita clique sem botao definido", async () => {
  const injector = new FakeInjector();
  const dispatcher = new RemoteInputDispatcher(injector, () => ({ width: 800, height: 600 }));
  await assert.rejects(() => dispatcher.dispatch({ type: "input-mouse", kind: "down", x: 0, y: 0 }));
});

test("RemoteInputDispatcher encaminha eventos de teclado sem alteracao", async () => {
  const injector = new FakeInjector();
  const dispatcher = new RemoteInputDispatcher(injector, () => ({ width: 800, height: 600 }));
  const keyEvent: RemoteKeyboardEvent = {
    type: "input-keyboard",
    kind: "down",
    code: "KeyA",
    key: "a",
    modifiers: { ctrl: false, alt: false, shift: false, meta: false },
  };
  await dispatcher.dispatch(keyEvent);
  assert.deepEqual(injector.keys, [keyEvent]);
});
