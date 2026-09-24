import assert from "node:assert/strict";
import { test } from "node:test";
import { mapPointToNormalized } from "../src/renderer/app/video-mapping";

test("mapPointToNormalized centraliza corretamente sem letterbox (mesma proporcao)", () => {
  const rect = { left: 0, top: 0, width: 1000, height: 500 };
  const result = mapPointToNormalized(500, 250, rect, 1920, 960);
  assert.ok(result);
  assert.ok(Math.abs(result!.x - 0.5) < 1e-9);
  assert.ok(Math.abs(result!.y - 0.5) < 1e-9);
});

test("mapPointToNormalized calcula barras horizontais (letterbox lateral)", () => {
  // Elemento quadrado (1:1), video widescreen (16:9) -> barras nas laterais.
  const rect = { left: 0, top: 0, width: 1000, height: 1000 };
  const videoWidth = 1600;
  const videoHeight = 900;
  // Conteudo real: largura = altura * aspect = 1000 * (16/9) ~ 1777, maior que a largura do elemento
  // entao na verdade as barras ficam em cima/embaixo (videoAspect > elementAspect).
  const result = mapPointToNormalized(500, 500, rect, videoWidth, videoHeight);
  assert.ok(result);
  assert.ok(Math.abs(result!.x - 0.5) < 1e-9);
  assert.ok(Math.abs(result!.y - 0.5) < 1e-9);
});

test("mapPointToNormalized retorna null para clique fora da area real (na barra)", () => {
  const rect = { left: 0, top: 0, width: 1000, height: 1000 };
  const result = mapPointToNormalized(500, 10, rect, 1600, 900); // perto do topo, dentro da barra
  assert.equal(result, null);
});

test("mapPointToNormalized retorna null quando video ainda nao tem dimensoes", () => {
  const rect = { left: 0, top: 0, width: 1000, height: 500 };
  const result = mapPointToNormalized(100, 100, rect, 0, 0);
  assert.equal(result, null);
});

test("mapPointToNormalized considera o deslocamento (offset) do elemento na tela", () => {
  const rect = { left: 200, top: 100, width: 800, height: 600 };
  const result = mapPointToNormalized(600, 400, rect, 800, 600);
  assert.ok(result);
  assert.ok(Math.abs(result!.x - 0.5) < 1e-9);
  assert.ok(Math.abs(result!.y - 0.5) < 1e-9);
});
