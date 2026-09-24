import jwt from "jsonwebtoken";
import type { LicenseStatus } from "../ipc-contract";

/**
 * Chave publica do license-server (par de `NEXODESK_LICENSE_PRIVATE_KEY` no
 * servidor - ver packages/license-server/src/keys.ts). Verificar com a chave
 * publica funciona OFFLINE: o Controlador nao precisa falar com o
 * license-server toda vez que abre, so quando uma licenca nova e colada.
 *
 * Sem `NEXODESK_LICENSE_PUBLIC_KEY` configurada, nenhuma licenca valida (o app
 * funciona no plano Gratuito). Configure a mesma chave publica emitida pelo
 * seu license-server para reconhecer licencas Pro/Business.
 */
function getPublicKey(): string | null {
  return process.env.NEXODESK_LICENSE_PUBLIC_KEY ?? null;
}

interface LicenseClaims {
  sub: string;
  plan: "gratuito" | "pro" | "business";
  jti: string;
}

export function checkLicenseToken(token: string | null): LicenseStatus {
  if (!token) {
    return { hasToken: false, valid: false, planId: null };
  }
  const publicKey = getPublicKey();
  if (!publicKey) {
    return { hasToken: true, valid: false, planId: null, reason: "servidor-de-licenca-nao-configurado" };
  }
  try {
    const decoded = jwt.verify(token, publicKey, { algorithms: ["RS256"], issuer: "nexodesk-license-server" }) as LicenseClaims;
    return { hasToken: true, valid: true, planId: decoded.plan };
  } catch (err) {
    if (err instanceof jwt.TokenExpiredError) {
      return { hasToken: true, valid: false, planId: null, reason: "expirada" };
    }
    return { hasToken: true, valid: false, planId: null, reason: "assinatura-invalida" };
  }
}
