import assert from "node:assert/strict";
import { test } from "node:test";
import { ClipboardEchoGuard } from "../src/clipboard-guard";

test("shouldForward permite conteudo novo, nunca aplicado remotamente", () => {
  const guard = new ClipboardEchoGuard();
  assert.equal(guard.shouldForward("ola mundo"), true);
});

test("shouldForward bloqueia o eco imediato do que acabou de ser aplicado", () => {
  const guard = new ClipboardEchoGuard();
  guard.markApplied("texto vindo do controlador");
  assert.equal(guard.shouldForward("texto vindo do controlador"), false);
});

test("shouldForward volta a permitir apos o usuario copiar algo diferente", () => {
  const guard = new ClipboardEchoGuard();
  guard.markApplied("texto vindo do controlador");
  assert.equal(guard.shouldForward("outro texto copiado pelo cliente"), true);
});
