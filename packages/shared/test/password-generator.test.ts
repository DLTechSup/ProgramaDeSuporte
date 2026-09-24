import assert from "node:assert/strict";
import { test } from "node:test";
import { checkUnattendedPasswordStrength, generateSessionPassword } from "../src/password-generator";

test("generateSessionPassword respeita o tamanho pedido", () => {
  assert.equal(generateSessionPassword(6).length, 6);
  assert.equal(generateSessionPassword(8).length, 8);
});

test("generateSessionPassword nao usa caracteres ambiguos", () => {
  const password = generateSessionPassword(200);
  assert.doesNotMatch(password, /[01OIL]/);
});

test("checkUnattendedPasswordStrength rejeita senha fraca", () => {
  const result = checkUnattendedPasswordStrength("abc");
  assert.equal(result.ok, false);
  assert.ok(result.problems.length > 0);
});

test("checkUnattendedPasswordStrength aceita senha forte", () => {
  const result = checkUnattendedPasswordStrength("SenhaForte123");
  assert.equal(result.ok, true);
  assert.deepEqual(result.problems, []);
});
