import { randomUUID } from "node:crypto";
import jwt from "jsonwebtoken";
import type { PlanId } from "./plans";
import { getPlan } from "./plans";

export interface LicenseClaims {
  /** Identifica o cliente/assinante (e-mail). */
  sub: string;
  plan: PlanId;
  /** Identificador unico da licenca, usado para permitir revogacao. */
  jti: string;
}

export interface IssuedLicense {
  token: string;
  claims: LicenseClaims;
  expiresAt: Date;
}

const DEFAULT_VALIDITY_DAYS = 30;

export function issueLicense(
  privateKey: string,
  email: string,
  planId: PlanId,
  validityDays: number = DEFAULT_VALIDITY_DAYS
): IssuedLicense {
  getPlan(planId); // valida que o plano existe antes de emitir
  const claims: LicenseClaims = { sub: email, plan: planId, jti: randomUUID() };
  const expiresInSeconds = validityDays * 24 * 60 * 60;
  const token = jwt.sign(claims, privateKey, { algorithm: "RS256", expiresIn: expiresInSeconds, issuer: "nexodesk-license-server" });
  const expiresAt = new Date(Date.now() + expiresInSeconds * 1000);
  return { token, claims, expiresAt };
}

export type LicenseVerificationResult =
  | { valid: true; claims: LicenseClaims & { exp: number; iat: number } }
  | { valid: false; reason: "expirada" | "assinatura-invalida" | "revogada" };

export function verifyLicenseToken(
  publicKey: string,
  token: string,
  isRevoked: (jti: string) => boolean = () => false
): LicenseVerificationResult {
  try {
    const decoded = jwt.verify(token, publicKey, {
      algorithms: ["RS256"],
      issuer: "nexodesk-license-server",
    }) as LicenseClaims & { exp: number; iat: number };
    if (isRevoked(decoded.jti)) {
      return { valid: false, reason: "revogada" };
    }
    return { valid: true, claims: decoded };
  } catch (err) {
    if (err instanceof jwt.TokenExpiredError) {
      return { valid: false, reason: "expirada" };
    }
    return { valid: false, reason: "assinatura-invalida" };
  }
}
