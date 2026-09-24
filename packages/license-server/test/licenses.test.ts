import assert from "node:assert/strict";
import { test } from "node:test";
import { generateKeyPairSync } from "node:crypto";
import { issueLicense, verifyLicenseToken } from "../src/licenses";

function makeKeys() {
  return generateKeyPairSync("rsa", {
    modulusLength: 2048,
    publicKeyEncoding: { type: "spki", format: "pem" },
    privateKeyEncoding: { type: "pkcs8", format: "pem" },
  });
}

test("issueLicense gera um token valido para o par de chaves correto", () => {
  const { privateKey, publicKey } = makeKeys();
  const issued = issueLicense(privateKey, "cliente@example.com", "pro");
  const result = verifyLicenseToken(publicKey, issued.token);
  assert.equal(result.valid, true);
  if (result.valid) {
    assert.equal(result.claims.sub, "cliente@example.com");
    assert.equal(result.claims.plan, "pro");
  }
});

test("verifyLicenseToken rejeita token assinado com outra chave privada", () => {
  const { privateKey: outraChave } = makeKeys();
  const { publicKey } = makeKeys();
  const issued = issueLicense(outraChave, "cliente@example.com", "pro");
  const result = verifyLicenseToken(publicKey, issued.token);
  assert.equal(result.valid, false);
  if (!result.valid) {
    assert.equal(result.reason, "assinatura-invalida");
  }
});

test("verifyLicenseToken rejeita token expirado", () => {
  const { privateKey, publicKey } = makeKeys();
  const issued = issueLicense(privateKey, "cliente@example.com", "gratuito", -1);
  const result = verifyLicenseToken(publicKey, issued.token);
  assert.equal(result.valid, false);
  if (!result.valid) {
    assert.equal(result.reason, "expirada");
  }
});

test("verifyLicenseToken rejeita token revogado mesmo com assinatura valida", () => {
  const { privateKey, publicKey } = makeKeys();
  const issued = issueLicense(privateKey, "cliente@example.com", "business");
  const result = verifyLicenseToken(publicKey, issued.token, (jti) => jti === issued.claims.jti);
  assert.equal(result.valid, false);
  if (!result.valid) {
    assert.equal(result.reason, "revogada");
  }
});

test("issueLicense rejeita plano desconhecido", () => {
  const { privateKey } = makeKeys();
  assert.throws(() => issueLicense(privateKey, "cliente@example.com", "inexistente" as never));
});
