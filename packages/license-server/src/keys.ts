import { generateKeyPairSync } from "node:crypto";

export interface LicenseKeyPair {
  privateKey: string;
  publicKey: string;
}

/**
 * As licencas sao assinadas com uma chave privada RSA que fica SOMENTE aqui no
 * servidor. Os aplicativos (Agent/Controller) embarcam apenas a chave PUBLICA
 * e conseguem validar uma licenca offline (sem chamar o servidor a cada
 * inicializacao) sabendo que ninguem alem deste servidor poderia te-la assinado.
 *
 * Em producao, `NEXODESK_LICENSE_PRIVATE_KEY` deve vir de um segredo gerenciado
 * (variavel de ambiente/cofre), nunca commitado no repositorio. Sem essa
 * variavel, um par de chaves e gerado em memoria ao subir o processo - util
 * para desenvolvimento, mas invalida licencas antigas a cada reinicio.
 */
export function loadOrCreateKeyPair(): LicenseKeyPair {
  const privateKeyFromEnv = process.env.NEXODESK_LICENSE_PRIVATE_KEY;
  const publicKeyFromEnv = process.env.NEXODESK_LICENSE_PUBLIC_KEY;
  if (privateKeyFromEnv && publicKeyFromEnv) {
    return { privateKey: privateKeyFromEnv, publicKey: publicKeyFromEnv };
  }

  const { privateKey, publicKey } = generateKeyPairSync("rsa", {
    modulusLength: 2048,
    publicKeyEncoding: { type: "spki", format: "pem" },
    privateKeyEncoding: { type: "pkcs8", format: "pem" },
  });
  return { privateKey, publicKey };
}
