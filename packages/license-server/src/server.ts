import express, { type Express, type NextFunction, type Request, type Response } from "express";
import { getPlan, isValidPlanId, listPlans } from "./plans";
import { issueLicense, verifyLicenseToken } from "./licenses";
import { LicenseStore } from "./store";
import type { LicenseKeyPair } from "./keys";

export interface LicenseServerOptions {
  keys: LicenseKeyPair;
  store?: LicenseStore;
  /**
   * Chave usada para proteger os endpoints administrativos (emitir/revogar
   * licenca). Em producao, a emissao deve ser chamada pelo seu backend de
   * pagamento (ex.: webhook do Stripe/Mercado Pago) - nunca exposta ao publico.
   */
  adminApiKey: string;
}

function requireAdminKey(adminApiKey: string) {
  return (req: Request, res: Response, next: NextFunction) => {
    if (req.header("x-admin-key") !== adminApiKey) {
      res.status(401).json({ erro: "Chave administrativa invalida ou ausente." });
      return;
    }
    next();
  };
}

export function createLicenseServer(options: LicenseServerOptions): Express {
  const store = options.store ?? new LicenseStore();
  const app = express();
  app.use(express.json());

  app.get("/planos", (_req, res) => {
    res.json({ planos: listPlans() });
  });

  app.get("/chave-publica", (_req, res) => {
    res.type("text/plain").send(options.keys.publicKey);
  });

  app.post("/licencas", requireAdminKey(options.adminApiKey), (req, res) => {
    const { email, plano, validadeDias } = req.body ?? {};
    if (typeof email !== "string" || !email.includes("@")) {
      res.status(400).json({ erro: "Informe um e-mail valido." });
      return;
    }
    if (typeof plano !== "string" || !isValidPlanId(plano)) {
      res.status(400).json({ erro: "Plano invalido. Use gratuito, pro ou business." });
      return;
    }
    const issued = issueLicense(options.keys.privateKey, email, plano, validadeDias);
    store.save({
      jti: issued.claims.jti,
      email,
      plan: plano,
      issuedAt: new Date(),
      expiresAt: issued.expiresAt,
      revoked: false,
    });
    res.status(201).json({ token: issued.token, expiraEm: issued.expiresAt.toISOString(), plano: getPlan(plano) });
  });

  app.post("/licencas/verificar", (req, res) => {
    const { token } = req.body ?? {};
    if (typeof token !== "string") {
      res.status(400).json({ erro: "Informe o token da licenca." });
      return;
    }
    const result = verifyLicenseToken(options.keys.publicKey, token, (jti) => store.isRevoked(jti));
    if (!result.valid) {
      res.status(200).json({ valido: false, motivo: result.reason });
      return;
    }
    res.status(200).json({ valido: true, plano: getPlan(result.claims.plan), email: result.claims.sub, expiraEm: new Date(result.claims.exp * 1000).toISOString() });
  });

  app.post("/licencas/revogar", requireAdminKey(options.adminApiKey), (req, res) => {
    const { jti } = req.body ?? {};
    if (typeof jti !== "string") {
      res.status(400).json({ erro: "Informe o jti da licenca a revogar." });
      return;
    }
    const ok = store.revoke(jti);
    res.status(ok ? 200 : 404).json({ revogado: ok });
  });

  app.get("/licencas/:email", requireAdminKey(options.adminApiKey), (req, res) => {
    const email = req.params.email ?? "";
    res.json({ licencas: store.listByEmail(email) });
  });

  return app;
}
