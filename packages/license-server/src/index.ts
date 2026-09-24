import { createLicenseServer } from "./server";
import { loadOrCreateKeyPair } from "./keys";

const PORT = Number(process.env.PORT ?? 8444);
const adminApiKey = process.env.NEXODESK_ADMIN_API_KEY;

if (!adminApiKey) {
  console.error(
    "[nexodesk-license] Defina a variavel de ambiente NEXODESK_ADMIN_API_KEY antes de iniciar (protege a emissao de licencas)."
  );
  process.exit(1);
}

const keys = loadOrCreateKeyPair();
if (!process.env.NEXODESK_LICENSE_PRIVATE_KEY) {
  console.warn(
    "[nexodesk-license] Nenhuma NEXODESK_LICENSE_PRIVATE_KEY configurada - usando um par de chaves gerado em memoria. " +
      "Todas as licencas emitidas serao invalidadas quando este processo reiniciar. Configure a variavel em producao."
  );
}

const app = createLicenseServer({ keys, adminApiKey });

app.listen(PORT, () => {
  console.info(`[nexodesk-license] ouvindo em http://0.0.0.0:${PORT}`);
});
