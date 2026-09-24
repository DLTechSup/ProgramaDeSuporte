import assert from "node:assert/strict";
import { test } from "node:test";
import {
  computePasswordProof,
  generateChallengeNonce,
  hashPasswordForStorage,
  sha256Hex,
  verifyPasswordProof,
  verifyStoredPassword,
} from "../src/crypto";

test("generateChallengeNonce produz valores unicos", () => {
  const a = generateChallengeNonce();
  const b = generateChallengeNonce();
  assert.notEqual(a, b);
  assert.match(a, /^[0-9a-f]{32}$/);
});

test("verifyPasswordProof aceita prova correta", () => {
  const nonce = generateChallengeNonce();
  const proof = computePasswordProof(nonce, "MinhaSenha123");
  assert.equal(verifyPasswordProof(nonce, "MinhaSenha123", proof), true);
});

test("verifyPasswordProof rejeita senha errada", () => {
  const nonce = generateChallengeNonce();
  const proof = computePasswordProof(nonce, "MinhaSenha123");
  assert.equal(verifyPasswordProof(nonce, "SenhaErrada", proof), false);
});

test("verifyPasswordProof rejeita nonce reaproveitado com prova de outro nonce", () => {
  const nonce1 = generateChallengeNonce();
  const nonce2 = generateChallengeNonce();
  const proof = computePasswordProof(nonce1, "MinhaSenha123");
  assert.equal(verifyPasswordProof(nonce2, "MinhaSenha123", proof), false);
});

test("hashPasswordForStorage nunca guarda a senha em texto puro", () => {
  const stored = hashPasswordForStorage("SenhaForte123");
  assert.notEqual(stored.hash, "SenhaForte123");
  assert.equal(verifyStoredPassword("SenhaForte123", stored), true);
  assert.equal(verifyStoredPassword("SenhaErrada", stored), false);
});

test("sha256Hex e deterministico", () => {
  const buf = Buffer.from("conteudo de teste");
  assert.equal(sha256Hex(buf), sha256Hex(buf));
});
