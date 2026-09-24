import assert from "node:assert/strict";
import { test } from "node:test";
import { formatAgentId, generateAgentId, isValidAgentId, normalizeAgentId } from "../src/id-generator";

test("generateAgentId produz 9 digitos", () => {
  const id = generateAgentId();
  assert.match(id, /^\d{9}$/);
});

test("generateAgentId produz valores variados", () => {
  const ids = new Set(Array.from({ length: 50 }, () => generateAgentId()));
  assert.ok(ids.size > 1, "esperava IDs diferentes entre chamadas");
});

test("formatAgentId agrupa em blocos de 3", () => {
  assert.equal(formatAgentId("123456789"), "123 456 789");
});

test("normalizeAgentId remove espacos e separadores", () => {
  assert.equal(normalizeAgentId("123 456-789"), "123456789");
});

test("isValidAgentId valida formato", () => {
  assert.equal(isValidAgentId("123 456 789"), true);
  assert.equal(isValidAgentId("12345"), false);
  assert.equal(isValidAgentId("abcdefghi"), false);
});
