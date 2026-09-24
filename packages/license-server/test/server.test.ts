import assert from "node:assert/strict";
import { test } from "node:test";
import type { Server } from "node:http";
import type { AddressInfo } from "node:net";
import { generateKeyPairSync } from "node:crypto";
import { createLicenseServer } from "../src/server";
import { LicenseStore } from "../src/store";

const ADMIN_KEY = "chave-admin-de-teste";

function makeKeys() {
  return generateKeyPairSync("rsa", {
    modulusLength: 2048,
    publicKeyEncoding: { type: "spki", format: "pem" },
    privateKeyEncoding: { type: "pkcs8", format: "pem" },
  });
}

async function startTestServer() {
  const keys = makeKeys();
  const store = new LicenseStore();
  const app = createLicenseServer({ keys, store, adminApiKey: ADMIN_KEY });
  const server: Server = await new Promise((resolve) => {
    const s = app.listen(0, () => resolve(s));
  });
  const { port } = server.address() as AddressInfo;
  return {
    baseUrl: `http://127.0.0.1:${port}`,
    close: () => new Promise<void>((resolve) => server.close(() => resolve())),
  };
}

test("GET /planos lista os tres planos publicamente", async () => {
  const server = await startTestServer();
  try {
    const res = await fetch(`${server.baseUrl}/planos`);
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.planos.length, 3);
    assert.ok(body.planos.some((p: { id: string }) => p.id === "gratuito"));
  } finally {
    await server.close();
  }
});

test("POST /licencas exige chave administrativa", async () => {
  const server = await startTestServer();
  try {
    const res = await fetch(`${server.baseUrl}/licencas`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email: "a@b.com", plano: "pro" }),
    });
    assert.equal(res.status, 401);
  } finally {
    await server.close();
  }
});

test("fluxo completo: emitir licenca, verificar, revogar e verificar de novo", async () => {
  const server = await startTestServer();
  try {
    const issueRes = await fetch(`${server.baseUrl}/licencas`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-admin-key": ADMIN_KEY },
      body: JSON.stringify({ email: "cliente@example.com", plano: "pro" }),
    });
    assert.equal(issueRes.status, 201);
    const { token, plano } = await issueRes.json();
    assert.equal(plano.id, "pro");

    const verifyRes = await fetch(`${server.baseUrl}/licencas/verificar`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ token }),
    });
    const verifyBody = await verifyRes.json();
    assert.equal(verifyBody.valido, true);
    assert.equal(verifyBody.email, "cliente@example.com");

    const decoded = JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString("utf8"));

    const revokeRes = await fetch(`${server.baseUrl}/licencas/revogar`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-admin-key": ADMIN_KEY },
      body: JSON.stringify({ jti: decoded.jti }),
    });
    assert.equal(revokeRes.status, 200);

    const verifyAfterRevoke = await fetch(`${server.baseUrl}/licencas/verificar`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ token }),
    });
    const verifyAfterRevokeBody = await verifyAfterRevoke.json();
    assert.equal(verifyAfterRevokeBody.valido, false);
    assert.equal(verifyAfterRevokeBody.motivo, "revogada");
  } finally {
    await server.close();
  }
});

test("POST /licencas rejeita plano invalido", async () => {
  const server = await startTestServer();
  try {
    const res = await fetch(`${server.baseUrl}/licencas`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-admin-key": ADMIN_KEY },
      body: JSON.stringify({ email: "a@b.com", plano: "platina" }),
    });
    assert.equal(res.status, 400);
  } finally {
    await server.close();
  }
});
